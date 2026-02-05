"""AODV (Ad-hoc On-demand Distance Vector) 프로토콜 구현."""
import copy
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from .base import RoutingProtocol
from ..core.node import Node
from ..core.packet import Packet, PacketType


@dataclass
class RouteEntry:
    """라우팅 테이블 엔트리."""
    destination: int
    next_hop: int
    hop_count: int
    sequence_number: int
    expiry_time: float
    is_valid: bool = True


@dataclass
class RREQEntry:
    """RREQ 처리 기록."""
    source_id: int
    broadcast_id: int
    timestamp: float


class AODV(RoutingProtocol):
    """AODV 프로토콜.

    반응적(Reactive) 라우팅 프로토콜.
    경로가 필요할 때만 RREQ/RREP를 통해 경로 탐색.
    경로 유지를 위한 RERR 메시지 지원.
    """

    ROUTE_TIMEOUT = 30.0       # 경로 기본 만료 시간 (10→30초)
    ACTIVE_ROUTE_TIMEOUT = 10.0  # 활성 경로 연장 시간
    RREQ_TIMEOUT = 5.0         # 탐색 중복 방지 시간 (3→5초)
    MAX_RREQ_RETRIES = 3
    PATH_DISCOVERY_TIME = 5.0

    def __init__(self, node: Node):
        super().__init__(node)
        self.route_table: Dict[int, RouteEntry] = {}
        self.rreq_id: int = 0
        self.processed_rreqs: Dict[tuple, RREQEntry] = {}  # (source, broadcast_id) -> entry
        self.pending_discoveries: Dict[int, float] = {}  # destination -> discovery_start_time
        self.pending_rreq_forwards: List[Packet] = []  # 다음 스텝에서 포워딩할 RREQ
        self.pending_rrep_unicasts: List[tuple] = []  # [(next_hop_id, packet)] 유니캐스트
        self.sequence_number: int = 0
        self.current_sim_time: float = 0.0

    @property
    def name(self) -> str:
        return "AODV"

    def initialize(self) -> None:
        """AODV 초기화."""
        self.route_table.clear()
        self.processed_rreqs.clear()
        self.pending_discoveries.clear()
        self.rreq_id = 0

    def update(self, current_time: float) -> List[Packet]:
        """주기적 업데이트."""
        self.current_sim_time = current_time
        packets = []

        # 대기 중인 RREQ 포워딩 (한 스텝에 한 홉씩)
        if self.pending_rreq_forwards:
            packets.extend(self.pending_rreq_forwards)
            self.pending_rreq_forwards = []

        # 만료된 라우트 제거
        self._cleanup_expired_routes(current_time)

        # 만료된 RREQ 기록 제거
        expired = [(k, v) for k, v in self.processed_rreqs.items()
                   if current_time - v.timestamp > self.PATH_DISCOVERY_TIME]
        for key, _ in expired:
            del self.processed_rreqs[key]

        # 만료된 경로 탐색 요청 제거
        expired_disc = [dest for dest, start_time in self.pending_discoveries.items()
                        if current_time - start_time > self.RREQ_TIMEOUT]
        for dest in expired_disc:
            del self.pending_discoveries[dest]

        return packets

    def handle_packet(self, packet: Packet) -> Optional[Packet]:
        """패킷 처리."""
        if packet.packet_type == PacketType.RREQ:
            return self._handle_rreq(packet)

        elif packet.packet_type == PacketType.RREP:
            return self._handle_rrep(packet)

        elif packet.packet_type == PacketType.RERR:
            return self._handle_rerr(packet)

        elif packet.packet_type == PacketType.DATA:
            return self._handle_data(packet)

        return None

    def get_next_hop(self, destination_id: int) -> Optional[int]:
        """다음 홉 조회. 경로 사용 시 만료 시간 연장."""
        if destination_id in self.route_table:
            route = self.route_table[destination_id]
            if route.is_valid and self.current_sim_time <= route.expiry_time:
                # 다음 홉이 실제로 이웃인지 확인 (링크 유효성 검사)
                if route.next_hop not in self.node.neighbors:
                    # 링크 끊김 - 경로 무효화
                    route.is_valid = False
                    self.route_failures += 1
                    return None

                # 경로 사용 시 만료 시간 연장 (Active Route Timeout)
                route.expiry_time = self.current_sim_time + self.ACTIVE_ROUTE_TIMEOUT
                return route.next_hop

        return None

    def is_discovering(self, destination_id: int) -> bool:
        """이미 경로 탐색 중인지 확인."""
        return destination_id in self.pending_discoveries

    def get_pending_unicasts(self) -> List[tuple]:
        """대기 중인 유니캐스트 패킷 반환 [(next_hop_id, packet)]."""
        unicasts = self.pending_rrep_unicasts
        self.pending_rrep_unicasts = []
        return unicasts

    def discover_route(self, destination_id: int) -> Optional[Packet]:
        """경로 탐색을 위한 RREQ 생성."""
        # 이미 탐색 중이면 None 반환
        if destination_id in self.pending_discoveries:
            return None

        self.pending_discoveries[destination_id] = self.current_sim_time
        self.rreq_id += 1
        self.sequence_number += 1
        self.route_discoveries += 1
        self.control_packets_sent += 1

        dest_seq = 0
        if destination_id in self.route_table:
            dest_seq = self.route_table[destination_id].sequence_number

        return Packet(
            packet_id=self.rreq_id,
            packet_type=PacketType.RREQ,
            source_id=self.node.node_id,
            destination_id=destination_id,
            ttl=64,
            hop_count=0,
            sequence_number=self.sequence_number,
            broadcast_id=self.rreq_id,
            dest_sequence=dest_seq,
            path=[self.node.node_id]
        )

    def _handle_rreq(self, packet: Packet) -> Optional[Packet]:
        """RREQ 처리."""
        self.control_packets_received += 1

        # 중복 RREQ 확인
        rreq_key = (packet.source_id, packet.broadcast_id)
        if rreq_key in self.processed_rreqs:
            return None

        self.processed_rreqs[rreq_key] = RREQEntry(
            source_id=packet.source_id,
            broadcast_id=packet.broadcast_id,
            timestamp=self.current_sim_time
        )

        # 역방향 경로 설정 (source로 가는 경로)
        self._update_route(
            packet.source_id,
            packet.path[-1] if packet.path else packet.source_id,
            packet.hop_count + 1,
            packet.sequence_number
        )

        # 목적지인 경우 RREP 응답
        if packet.destination_id == self.node.node_id:
            self.sequence_number += 1
            return self._create_rrep(packet)

        # 목적지까지 유효한 경로가 있으면 RREP 응답
        if packet.destination_id in self.route_table:
            route = self.route_table[packet.destination_id]
            if route.is_valid and route.sequence_number >= packet.dest_sequence:
                return self._create_intermediate_rrep(packet, route)

        # RREQ 포워딩 - 다음 스텝에서 브로드캐스트
        if packet.ttl > 0:
            forwarded = copy.deepcopy(packet)
            forwarded.ttl -= 1
            forwarded.hop_count += 1
            forwarded.path.append(self.node.node_id)
            self.pending_rreq_forwards.append(forwarded)
            self.control_packets_sent += 1

        return None

    def _handle_rrep(self, packet: Packet) -> Optional[Packet]:
        """RREP 처리."""
        self.control_packets_received += 1

        # 순방향 경로 설정 (destination으로 가는 경로)
        prev_hop = packet.path[-1] if packet.path else packet.source_id
        self._update_route(
            packet.source_id,  # RREP의 source는 원래 목적지
            prev_hop,
            packet.hop_count,
            packet.sequence_number
        )

        # 원래 요청자에게 전달 (RREP 도착 = 경로 확립 완료)
        if packet.destination_id == self.node.node_id:
            # 경로가 확립되면 엔진의 pending_packets에서 대기 중인
            # DATA 패킷들이 자동으로 전송됨 (엔진이 처리)
            return None

        # RREP 포워딩 (유니캐스트 - 특정 다음 홉으로만)
        if packet.destination_id in self.route_table:
            route = self.route_table[packet.destination_id]
            if route.is_valid:
                # 역방향 경로도 갱신 (RREP 전달 경로)
                route.expiry_time = self.current_sim_time + self.ROUTE_TIMEOUT

                forwarded = copy.deepcopy(packet)
                forwarded.hop_count += 1
                forwarded.path.append(self.node.node_id)
                # 유니캐스트로 다음 홉에게만 전달
                self.pending_rrep_unicasts.append((route.next_hop, forwarded))
                self.control_packets_sent += 1

        return None

    def _handle_rerr(self, packet: Packet) -> Optional[Packet]:
        """RERR 처리."""
        self.control_packets_received += 1

        # 해당 경로 무효화
        dest_id = packet.destination_id
        if dest_id in self.route_table:
            self.route_table[dest_id].is_valid = False
            self.route_failures += 1

            # RERR 포워딩
            if packet.ttl > 0:
                packet.ttl -= 1
                self.control_packets_sent += 1
                return packet

        return None

    def _handle_data(self, packet: Packet) -> Optional[Packet]:
        """데이터 패킷 처리.

        참고: DATA 패킷은 엔진의 _process_packets()에서 직접 처리됨.
        이 핸들러는 경로 타임아웃 갱신만 수행.
        """
        if packet.destination_id == self.node.node_id:
            # 도착 - 역방향 경로 갱신 (응답 패킷용)
            if packet.source_id in self.route_table:
                self.route_table[packet.source_id].expiry_time = \
                    self.current_sim_time + self.ACTIVE_ROUTE_TIMEOUT
            return None

        # 역방향 경로 갱신 (source로 돌아가는 경로)
        if packet.source_id in self.route_table:
            self.route_table[packet.source_id].expiry_time = \
                self.current_sim_time + self.ACTIVE_ROUTE_TIMEOUT

        # 실제 포워딩은 엔진이 처리 (hop_count, path는 엔진에서 관리)
        return None

    def _create_rrep(self, rreq: Packet) -> Packet:
        """RREP 생성."""
        self.control_packets_sent += 1
        return Packet(
            packet_id=rreq.packet_id,
            packet_type=PacketType.RREP,
            source_id=self.node.node_id,
            destination_id=rreq.source_id,
            ttl=64,
            hop_count=0,
            sequence_number=self.sequence_number,
            path=[self.node.node_id]
        )

    def _create_intermediate_rrep(self, rreq: Packet, route: RouteEntry) -> Packet:
        """중간 노드에서 RREP 생성."""
        self.control_packets_sent += 1
        return Packet(
            packet_id=rreq.packet_id,
            packet_type=PacketType.RREP,
            source_id=rreq.destination_id,
            destination_id=rreq.source_id,
            ttl=64,
            hop_count=route.hop_count,
            sequence_number=route.sequence_number,
            path=[self.node.node_id]
        )

    def _update_route(self, destination: int, next_hop: int,
                      hop_count: int, seq_num: int) -> None:
        """라우팅 테이블 업데이트."""
        current_time = self.current_sim_time

        # 경로 발견되면 pending_discoveries에서 제거
        if destination in self.pending_discoveries:
            del self.pending_discoveries[destination]

        if destination in self.route_table:
            existing = self.route_table[destination]
            # 더 새로운 시퀀스 번호 또는 더 짧은 경로
            if seq_num > existing.sequence_number or \
               (seq_num == existing.sequence_number and hop_count < existing.hop_count):
                self.route_table[destination] = RouteEntry(
                    destination=destination,
                    next_hop=next_hop,
                    hop_count=hop_count,
                    sequence_number=seq_num,
                    expiry_time=current_time + self.ROUTE_TIMEOUT
                )
        else:
            self.route_table[destination] = RouteEntry(
                destination=destination,
                next_hop=next_hop,
                hop_count=hop_count,
                sequence_number=seq_num,
                expiry_time=current_time + self.ROUTE_TIMEOUT
            )

        # 내부 라우팅 테이블도 동기화
        self.routing_table[destination] = next_hop

    def _cleanup_expired_routes(self, current_time: float) -> None:
        """만료된 경로 제거."""
        expired = [dest for dest, route in self.route_table.items()
                   if current_time > route.expiry_time]
        for dest in expired:
            del self.route_table[dest]
            if dest in self.routing_table:
                del self.routing_table[dest]
