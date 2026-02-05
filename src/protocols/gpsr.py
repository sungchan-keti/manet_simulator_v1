"""GPSR (Greedy Perimeter Stateless Routing) 프로토콜 구현."""
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

from .base import RoutingProtocol
from ..core.node import Node
from ..core.packet import Packet, PacketType
from ..core.position import Position

if TYPE_CHECKING:
    from ..core.location_service import LocationService


@dataclass
class NeighborLocation:
    """이웃 노드 위치 정보."""
    node_id: int
    position: Position
    last_beacon_time: float


class GPSR(RoutingProtocol):
    """GPSR 프로토콜.

    위치 기반(Geographic) 라우팅 프로토콜.
    Greedy 포워딩: 목적지에 가장 가까운 이웃으로 전송.
    Perimeter 모드: Greedy 실패 시 우회 경로 사용.
    """

    BEACON_INTERVAL = 1.0  # seconds
    NEIGHBOR_TIMEOUT = 3.0

    # Shared location service (set by SimulationEngine for all GPSR instances)
    _shared_location_service: Optional['LocationService'] = None

    @classmethod
    def set_shared_location_service(cls, service: 'LocationService') -> None:
        """Set the shared location service for all GPSR instances."""
        cls._shared_location_service = service

    def __init__(self, node: Node):
        super().__init__(node)
        self.neighbor_locations: Dict[int, NeighborLocation] = {}
        # Legacy per-node dictionary (deprecated, use shared service instead)
        self._local_destination_locations: Dict[int, Position] = {}
        self.last_beacon_time: float = -self.BEACON_INTERVAL  # 즉시 첫 비콘 전송
        self.current_sim_time: float = 0.0

    @property
    def destination_locations(self) -> Dict[int, Position]:
        """Get destination locations from shared service or local fallback.

        Returns the shared location service's positions if available,
        otherwise falls back to local dictionary for backward compatibility.
        """
        if self._shared_location_service is not None:
            return self._shared_location_service._positions
        return self._local_destination_locations

    @property
    def name(self) -> str:
        return "GPSR"

    def initialize(self) -> None:
        """GPSR 초기화."""
        self.neighbor_locations.clear()
        self.routing_table.clear()

    def update(self, current_time: float) -> List[Packet]:
        """주기적 비콘 전송."""
        self.current_sim_time = current_time
        packets = []

        # 비콘 메시지 전송
        if current_time - self.last_beacon_time >= self.BEACON_INTERVAL:
            packets.append(self._create_beacon())
            self.last_beacon_time = current_time

        # 만료된 이웃 제거
        self._cleanup_expired_neighbors(current_time)

        return packets

    def handle_packet(self, packet: Packet) -> Optional[Packet]:
        """패킷 처리."""
        if packet.packet_type == PacketType.BEACON:
            self._handle_beacon(packet)
            self.control_packets_received += 1
            return None

        elif packet.packet_type == PacketType.DATA:
            return self._handle_data(packet)

        return None

    def get_next_hop(self, destination_id: int) -> Optional[int]:
        """Greedy 또는 Perimeter 모드로 다음 홉 결정. 링크 유효성 검사 포함."""
        if destination_id not in self.destination_locations:
            return None

        dest_pos = self.destination_locations[destination_id]
        next_hop = self._greedy_next_hop(dest_pos)

        # 링크 유효성 검사: 다음 홉이 실제로 현재 이웃인지 확인
        if next_hop is not None and next_hop not in self.node.neighbors:
            self.route_failures += 1
            return None

        return next_hop

    def register_destination_location(self, node_id: int, position: Position) -> None:
        """목적지 위치 등록 (위치 서비스 시뮬레이션).

        If a shared location service is set, this updates the shared service.
        Otherwise, it falls back to the local dictionary.
        """
        if self._shared_location_service is not None:
            self._shared_location_service.update_position(node_id, position)
        else:
            self._local_destination_locations[node_id] = position

    def _create_beacon(self) -> Packet:
        """비콘 패킷 생성."""
        self.sequence_number += 1
        self.control_packets_sent += 1

        packet = Packet(
            packet_id=self.sequence_number,
            packet_type=PacketType.BEACON,
            source_id=self.node.node_id,
            destination_id=-1,  # 브로드캐스트
            ttl=1,
            sequence_number=self.sequence_number
        )
        # 위치 정보는 실제로는 payload에 인코딩
        packet.destination_position = (
            self.node.position.x,
            self.node.position.y,
            self.node.position.z
        )
        return packet

    def _handle_beacon(self, packet: Packet) -> None:
        """비콘 처리."""
        sender_id = packet.source_id

        if packet.destination_position:
            x, y, z = packet.destination_position
            position = Position(x, y, z)

            self.neighbor_locations[sender_id] = NeighborLocation(
                node_id=sender_id,
                position=position,
                last_beacon_time=self.current_sim_time
            )

    def _handle_data(self, packet: Packet) -> Optional[Packet]:
        """데이터 패킷 처리.

        참고: DATA 패킷은 엔진의 _process_packets()에서 직접 처리됨.
        이 핸들러는 greedy/perimeter 모드 전환 로직만 수행.
        """
        if packet.destination_id == self.node.node_id:
            return None  # 도착

        if not packet.destination_position:
            # 목적지 위치 정보 필요
            if packet.destination_id in self.destination_locations:
                pos = self.destination_locations[packet.destination_id]
                packet.destination_position = (pos.x, pos.y, pos.z)
            else:
                self.route_failures += 1
                return None

        x, y, z = packet.destination_position
        dest_pos = Position(x, y, z)

        # 모드에 따른 포워딩 결정
        if packet.mode == "greedy":
            next_hop = self._greedy_next_hop(dest_pos)
            if next_hop is None:
                # Greedy 실패 -> Perimeter 모드 전환
                packet.mode = "perimeter"
        else:
            # Perimeter 모드에서 목적지에 더 가까워지면 Greedy 복귀
            my_dist = self.node.position.distance_to(dest_pos)
            next_hop = self._greedy_next_hop(dest_pos)
            if next_hop is not None and next_hop in self.neighbor_locations:
                neighbor_dist = self.neighbor_locations[next_hop].position.distance_to(dest_pos)
                if neighbor_dist < my_dist:
                    packet.mode = "greedy"

        # 실제 포워딩은 엔진이 처리 (hop_count, path는 엔진에서 관리)
        return None

    def _greedy_next_hop(self, dest_pos: Position) -> Optional[int]:
        """Greedy 포워딩: 목적지에 가장 가까운 이웃 선택."""
        my_distance = self.node.position.distance_to(dest_pos)
        best_neighbor = None
        best_distance = my_distance

        for neighbor_id, neighbor_info in self.neighbor_locations.items():
            dist = neighbor_info.position.distance_to(dest_pos)
            if dist < best_distance:
                best_distance = dist
                best_neighbor = neighbor_id

        return best_neighbor

    def _perimeter_next_hop(self, dest_pos: Position,
                            prev_hop: Optional[int]) -> Optional[int]:
        """Perimeter 포워딩: Right-hand rule."""
        if not self.neighbor_locations:
            return None

        # 현재 노드에서 목적지 방향 벡터
        dx = dest_pos.x - self.node.position.x
        dy = dest_pos.y - self.node.position.y
        ref_angle = math.atan2(dy, dx)

        # 이전 홉에서 온 방향 (없으면 목적지 반대 방향)
        if prev_hop and prev_hop in self.neighbor_locations:
            prev_pos = self.neighbor_locations[prev_hop].position
            incoming_dx = self.node.position.x - prev_pos.x
            incoming_dy = self.node.position.y - prev_pos.y
            ref_angle = math.atan2(incoming_dy, incoming_dx)

        # Right-hand rule: 시계 반대 방향으로 첫 번째 이웃
        candidates = []
        for neighbor_id, neighbor_info in self.neighbor_locations.items():
            if neighbor_id == prev_hop:
                continue  # 왔던 곳으로 돌아가지 않음

            ndx = neighbor_info.position.x - self.node.position.x
            ndy = neighbor_info.position.y - self.node.position.y
            neighbor_angle = math.atan2(ndy, ndx)

            # 각도 차이 (시계 반대 방향)
            angle_diff = neighbor_angle - ref_angle
            if angle_diff < 0:
                angle_diff += 2 * math.pi

            candidates.append((neighbor_id, angle_diff))

        if candidates:
            # 가장 작은 각도 차이 (시계 반대 방향 첫 번째)
            candidates.sort(key=lambda x: x[1])
            return candidates[0][0]

        return None

    def _cleanup_expired_neighbors(self, current_time: float) -> None:
        """만료된 이웃 제거."""
        expired = [nid for nid, info in self.neighbor_locations.items()
                   if current_time - info.last_beacon_time > self.NEIGHBOR_TIMEOUT]
        for nid in expired:
            del self.neighbor_locations[nid]
