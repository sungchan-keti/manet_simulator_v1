"""네트워크 노드 모듈."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, TYPE_CHECKING
from enum import Enum

from .position import Position
from .packet import Packet
from .energy import EnergyModel, NodeEnergy

if TYPE_CHECKING:
    from ..protocols.base import RoutingProtocol


class NodeType(Enum):
    """노드 유형."""
    UGV = "ugv"
    UAV = "uav"
    GCS = "gcs"  # Ground Control Station


@dataclass
class Node:
    """네트워크 노드 (UGV 또는 UAV)."""
    node_id: int
    node_type: NodeType
    position: Position
    transmission_range: float = 250.0  # 미터

    # 상태
    is_active: bool = True

    # 에너지 모델
    energy_model: EnergyModel = field(default_factory=EnergyModel)
    node_energy: NodeEnergy = field(default_factory=lambda: NodeEnergy(
        initial_energy=10000.0,
        current_energy=10000.0
    ))

    # 네트워크 상태
    # Using Set[int] instead of Dict[int, Node] to avoid circular references
    # and reduce memory usage. Node objects are retrieved via Network.get_node()
    neighbors: set = field(default_factory=set)
    routing_protocol: Optional['RoutingProtocol'] = None

    # 통계
    packets_sent: int = 0
    packets_received: int = 0
    packets_forwarded: int = 0
    packets_dropped: int = 0

    def __post_init__(self):
        """초기화 후 처리."""
        # GCS는 무한 에너지 (전원 연결)
        if self.node_type == NodeType.GCS:
            self.node_energy.initial_energy = float('inf')
            self.node_energy.current_energy = float('inf')

    @property
    def energy(self) -> float:
        """현재 에너지 잔량 (%)."""
        return self.node_energy.remaining_ratio * 100

    def is_in_range(self, other: 'Node') -> bool:
        """다른 노드가 전송 범위 내에 있는지 확인."""
        distance = self.position.distance_to(other.position)
        return distance <= self.transmission_range

    def update_neighbors(self, all_nodes: List['Node']) -> None:
        """이웃 노드 목록 갱신 (legacy O(n) method - use update_neighbors_from_candidates instead)."""
        self.neighbors.clear()
        for node in all_nodes:
            if node.node_id != self.node_id and node.is_active and self.is_in_range(node):
                self.neighbors.add(node.node_id)

    def update_neighbors_from_candidates(
        self,
        candidate_ids: 'set[int]',
        nodes_dict: 'dict[int, Node]'
    ) -> None:
        """이웃 노드 목록 갱신 (optimized with spatial filtering).

        Args:
            candidate_ids: Set of node IDs that are potential neighbors
                          (pre-filtered by spatial index)
            nodes_dict: Dictionary mapping node IDs to Node objects
        """
        self.neighbors.clear()
        for node_id in candidate_ids:
            if node_id == self.node_id:
                continue
            node = nodes_dict.get(node_id)
            if node and node.is_active and self.is_in_range(node):
                self.neighbors.add(node_id)

    def send_packet(self, packet: Packet, distance: float = 0) -> bool:
        """패킷 전송.

        Args:
            packet: 전송할 패킷
            distance: 전송 거리 (거리 기반 에너지 계산용)

        Returns:
            성공 여부
        """
        if not self.is_active or not self.node_energy.is_alive:
            return False

        packet_size = packet.size
        tx_energy = self.energy_model.calculate_tx_energy(packet_size, distance)

        if not self.node_energy.consume_tx_energy(tx_energy, packet_size):
            self.is_active = False
            return False

        self.packets_sent += 1
        return True

    def receive_packet(self, packet: Packet) -> bool:
        """패킷 수신.

        Args:
            packet: 수신한 패킷

        Returns:
            성공 여부
        """
        if not self.is_active or not self.node_energy.is_alive:
            return False

        packet_size = packet.size
        rx_energy = self.energy_model.calculate_rx_energy(packet_size)

        if not self.node_energy.consume_rx_energy(rx_energy, packet_size):
            self.is_active = False
            return False

        self.packets_received += 1
        return True

    def consume_idle_energy(self, duration: float) -> bool:
        """유휴 에너지 소비.

        Args:
            duration: 유휴 시간 (seconds)

        Returns:
            성공 여부
        """
        if not self.is_active or not self.node_energy.is_alive:
            return False

        # GCS는 에너지 무제한
        if self.node_type == NodeType.GCS:
            return True

        idle_energy = self.energy_model.calculate_idle_energy(duration)

        if not self.node_energy.consume_idle_energy(idle_energy):
            self.is_active = False
            return False

        return True

    def get_energy_stats(self) -> dict:
        """에너지 통계 반환."""
        return {
            'initial_energy': self.node_energy.initial_energy,
            'current_energy': self.node_energy.current_energy,
            'remaining_ratio': self.node_energy.remaining_ratio,
            'tx_energy': self.node_energy.tx_energy_consumed,
            'rx_energy': self.node_energy.rx_energy_consumed,
            'idle_energy': self.node_energy.idle_energy_consumed,
            'total_consumed': self.node_energy.total_energy_consumed,
            'packets_tx': self.node_energy.packets_transmitted,
            'packets_rx': self.node_energy.packets_received,
            'bytes_tx': self.node_energy.bytes_transmitted,
            'bytes_rx': self.node_energy.bytes_received,
        }
