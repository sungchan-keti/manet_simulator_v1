"""OLSR (Optimized Link State Routing) 프로토콜 구현."""
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import deque

from .base import RoutingProtocol
from ..core.node import Node
from ..core.packet import Packet, PacketType


@dataclass
class OLSRNeighborInfo:
    """이웃 노드 정보."""
    node_id: int
    two_hop_neighbors: Set[int] = field(default_factory=set)  # 이 이웃을 통해 도달 가능한 2홉 이웃
    is_mpr: bool = False  # 내가 이 이웃을 MPR로 선택했는지
    last_hello_time: float = 0.0


@dataclass
class TopologyEntry:
    """토폴로지 테이블 엔트리."""
    dest_addr: int      # 목적지 (TC 발신자)
    last_addr: int      # 목적지에 도달하기 위한 마지막 홉 (MPR selector)
    sequence_number: int
    expiry_time: float


class OLSR(RoutingProtocol):
    """OLSR 프로토콜.

    선제적(Proactive) 라우팅 프로토콜.
    주기적으로 HELLO/TC 메시지를 교환하여 전체 토폴로지 파악.
    MPR(Multi-Point Relay) 선택으로 오버헤드 최소화.
    """

    HELLO_INTERVAL = 1.0  # seconds (더 빠른 수렴을 위해 단축)
    TC_INTERVAL = 2.0     # seconds
    NEIGHBOR_HOLD_TIME = 3.0
    TOP_HOLD_TIME = 6.0

    def __init__(self, node: Node):
        super().__init__(node)
        self.neighbors: Dict[int, OLSRNeighborInfo] = {}
        self.mpr_set: Set[int] = set()  # 내가 선택한 MPR들
        self.mpr_selector_set: Set[int] = set()  # 나를 MPR로 선택한 노드들
        # 토폴로지 테이블: (dest, last_hop) -> entry
        self.topology_table: Dict[Tuple[int, int], TopologyEntry] = {}
        # 처리된 TC 시퀀스 번호 추적
        self.tc_seq_numbers: Dict[int, int] = {}  # originator -> last_seq

        self.last_hello_time: float = -self.HELLO_INTERVAL
        self.last_tc_time: float = -self.TC_INTERVAL
        self.current_sim_time: float = 0.0

    @property
    def name(self) -> str:
        return "OLSR"

    def initialize(self) -> None:
        """OLSR 초기화."""
        self.neighbors.clear()
        self.mpr_set.clear()
        self.mpr_selector_set.clear()
        self.topology_table.clear()
        self.routing_table.clear()

    def update(self, current_time: float) -> List[Packet]:
        """주기적 HELLO/TC 메시지 생성."""
        self.current_sim_time = current_time
        packets = []

        # HELLO 메시지 (항상 전송)
        if current_time - self.last_hello_time >= self.HELLO_INTERVAL:
            packets.append(self._create_hello_packet())
            self.last_hello_time = current_time

        # TC 메시지 (MPR selector가 있는 경우, 즉 다른 노드가 나를 MPR로 선택한 경우)
        # 또는 이웃이 있는 경우 항상 전송 (멀티홉 지원)
        if current_time - self.last_tc_time >= self.TC_INTERVAL:
            if self.mpr_selector_set or self.neighbors:
                packets.append(self._create_tc_packet())
                self.last_tc_time = current_time

        # 만료된 엔트리 제거
        self._cleanup_expired_entries(current_time)

        return packets

    def handle_packet(self, packet: Packet) -> Optional[Packet]:
        """패킷 처리."""
        if packet.packet_type == PacketType.HELLO:
            self._handle_hello(packet)
            self.control_packets_received += 1
            return None

        elif packet.packet_type == PacketType.TC:
            should_forward = self._handle_tc(packet)
            self.control_packets_received += 1
            # TC 메시지 포워딩 (중복이 아니고 TTL이 남은 경우)
            # TTL > 1 체크: 감소 후에도 최소 1 이상이어야 포워딩
            if should_forward and packet.ttl > 1:
                packet.ttl -= 1
                packet.hop_count += 1
                self.control_packets_sent += 1
                return packet
            return None

        elif packet.packet_type == PacketType.DATA:
            # DATA 패킷은 엔진의 _process_packets()에서 직접 처리됨
            # 이 핸들러는 호출되지 않지만, 호출될 경우 무시
            return None

        return None

    def get_next_hop(self, destination_id: int) -> Optional[int]:
        """라우팅 테이블에서 다음 홉 조회. 링크 유효성 검사 포함."""
        next_hop = self.routing_table.get(destination_id)

        if next_hop is not None:
            # 다음 홉이 실제로 현재 이웃인지 확인 (링크 유효성 검사)
            if next_hop not in self.node.neighbors:
                # 링크 끊김 - 라우팅 테이블에서 제거
                del self.routing_table[destination_id]
                self.route_failures += 1
                return None

        return next_hop

    def _create_hello_packet(self) -> Packet:
        """HELLO 패킷 생성.

        payload에 이웃 목록과 MPR 정보를 인코딩.
        """
        self.sequence_number += 1
        self.control_packets_sent += 1

        # 이웃 목록과 MPR 정보를 payload에 저장
        # 형식: "neighbor_id:is_mpr,neighbor_id:is_mpr,..."
        neighbor_info = []
        for nid, info in self.neighbors.items():
            neighbor_info.append(f"{nid}:{1 if info.is_mpr else 0}")

        payload = ",".join(neighbor_info).encode() if neighbor_info else b""

        return Packet(
            packet_id=self.sequence_number,
            packet_type=PacketType.HELLO,
            source_id=self.node.node_id,
            destination_id=-1,
            ttl=1,
            sequence_number=self.sequence_number,
            payload=payload
        )

    def _create_tc_packet(self) -> Packet:
        """TC(Topology Control) 패킷 생성.

        자신의 이웃 목록을 advertise (MPR selector set 또는 전체 이웃).
        """
        self.sequence_number += 1
        self.control_packets_sent += 1

        # TC에 포함할 노드들 (나에게 도달 가능한 노드들)
        # MPR selector가 있으면 그것을, 없으면 모든 이웃을 advertise
        advertised_neighbors = self.mpr_selector_set if self.mpr_selector_set else set(self.neighbors.keys())
        payload = ",".join(str(n) for n in advertised_neighbors).encode() if advertised_neighbors else b""

        return Packet(
            packet_id=self.sequence_number,
            packet_type=PacketType.TC,
            source_id=self.node.node_id,
            destination_id=-1,
            ttl=255,
            sequence_number=self.sequence_number,
            payload=payload
        )

    def _handle_hello(self, packet: Packet) -> None:
        """HELLO 메시지 처리."""
        sender_id = packet.source_id

        # 이웃 테이블 갱신
        if sender_id not in self.neighbors:
            self.neighbors[sender_id] = OLSRNeighborInfo(
                node_id=sender_id,
                last_hello_time=self.current_sim_time
            )
        else:
            self.neighbors[sender_id].last_hello_time = self.current_sim_time

        # payload에서 sender의 이웃 목록과 MPR 정보 파싱
        sender_neighbors = set()
        if packet.payload:
            try:
                parts = packet.payload.decode().split(",")
                for part in parts:
                    if ":" in part:
                        nid_str, is_mpr_str = part.split(":")
                        nid = int(nid_str)
                        is_mpr = int(is_mpr_str) == 1
                        sender_neighbors.add(nid)

                        # sender가 나를 MPR로 선택했는지 확인
                        if nid == self.node.node_id and is_mpr:
                            self.mpr_selector_set.add(sender_id)
                        elif nid == self.node.node_id and not is_mpr:
                            self.mpr_selector_set.discard(sender_id)
            except (ValueError, UnicodeDecodeError):
                pass

        # sender를 통해 도달 가능한 2홉 이웃 업데이트
        self.neighbors[sender_id].two_hop_neighbors = sender_neighbors - {self.node.node_id}

        # MPR 재계산
        self._compute_mpr()
        # 라우팅 테이블 재계산
        self._compute_routing_table()

    def _handle_tc(self, packet: Packet) -> bool:
        """TC 메시지 처리. 포워딩 여부 반환."""
        originator = packet.source_id
        seq_num = packet.sequence_number

        # 자신이 보낸 TC는 무시
        if originator == self.node.node_id:
            return False

        # 중복 TC 확인 (더 오래된 시퀀스 번호면 무시)
        if originator in self.tc_seq_numbers:
            if seq_num <= self.tc_seq_numbers[originator]:
                return False

        self.tc_seq_numbers[originator] = seq_num

        # payload에서 advertised 이웃 파싱
        advertised_neighbors = set()
        if packet.payload:
            try:
                parts = packet.payload.decode().split(",")
                for part in parts:
                    if part.strip():
                        advertised_neighbors.add(int(part.strip()))
            except (ValueError, UnicodeDecodeError):
                pass

        # 토폴로지 테이블 갱신
        # TC originator는 advertised_neighbors를 통해 도달 가능
        # 즉, advertised_neighbor -> originator 경로가 존재
        for neighbor in advertised_neighbors:
            key = (originator, neighbor)  # (목적지, 마지막홉)
            self.topology_table[key] = TopologyEntry(
                dest_addr=originator,
                last_addr=neighbor,
                sequence_number=seq_num,
                expiry_time=self.current_sim_time + self.TOP_HOLD_TIME
            )

        # 라우팅 테이블 재계산
        self._compute_routing_table()

        return True  # 포워딩 필요

    def _compute_mpr(self) -> None:
        """MPR 집합 계산 (Greedy 알고리즘)."""
        self.mpr_set.clear()

        # 모든 이웃의 is_mpr 플래그 초기화
        for info in self.neighbors.values():
            info.is_mpr = False

        # 2홉 이웃 수집 (1홉 이웃이 아닌 노드들)
        all_two_hop = set()
        for nid, info in self.neighbors.items():
            for two_hop in info.two_hop_neighbors:
                if two_hop not in self.neighbors and two_hop != self.node.node_id:
                    all_two_hop.add(two_hop)

        uncovered = all_two_hop.copy()

        # Greedy MPR 선택
        while uncovered:
            best_neighbor = None
            best_coverage = 0

            for nid, info in self.neighbors.items():
                # 이 이웃을 통해 커버할 수 있는 2홉 이웃 수
                coverage = len(uncovered & info.two_hop_neighbors)
                if coverage > best_coverage:
                    best_coverage = coverage
                    best_neighbor = nid

            if best_neighbor is None or best_coverage == 0:
                break

            self.mpr_set.add(best_neighbor)
            self.neighbors[best_neighbor].is_mpr = True
            uncovered -= self.neighbors[best_neighbor].two_hop_neighbors

    def _compute_routing_table(self) -> None:
        """라우팅 테이블 계산 (BFS 기반).

        Uses proper BFS with a queue instead of unbounded while loop.
        Time complexity: O(V + E) where V is nodes and E is topology entries.
        """
        self.routing_table.clear()

        # Build adjacency list from topology table for efficient BFS
        # adjacency[last_hop] = list of destinations reachable from last_hop
        adjacency: Dict[int, List[int]] = {}
        for (dest, last_hop), entry in self.topology_table.items():
            if last_hop not in adjacency:
                adjacency[last_hop] = []
            adjacency[last_hop].append(dest)

        # BFS from this node
        # Queue contains (node_id, first_hop) pairs
        queue: deque = deque()

        # 1홉 이웃은 직접 도달 가능 (BFS starting points)
        for neighbor_id in self.neighbors:
            self.routing_table[neighbor_id] = neighbor_id
            queue.append((neighbor_id, neighbor_id))

        # BFS traversal with proper queue
        while queue:
            current, first_hop = queue.popleft()

            # Check all destinations reachable from current node
            for dest in adjacency.get(current, []):
                if dest not in self.routing_table:
                    # dest로 가려면 first_hop을 사용
                    self.routing_table[dest] = first_hop
                    queue.append((dest, first_hop))

    def _cleanup_expired_entries(self, current_time: float) -> None:
        """만료된 엔트리 제거."""
        # 이웃 정리
        expired_neighbors = [nid for nid, info in self.neighbors.items()
                            if current_time - info.last_hello_time > self.NEIGHBOR_HOLD_TIME]
        for nid in expired_neighbors:
            del self.neighbors[nid]
            self.mpr_selector_set.discard(nid)

        # 토폴로지 정리
        expired_topology = [key for key, entry in self.topology_table.items()
                          if current_time > entry.expiry_time]
        for key in expired_topology:
            del self.topology_table[key]

        if expired_neighbors or expired_topology:
            self._compute_mpr()
            self._compute_routing_table()
