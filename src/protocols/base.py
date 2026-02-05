"""라우팅 프로토콜 기본 클래스."""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.node import Node
    from ..core.packet import Packet


class RoutingProtocol(ABC):
    """라우팅 프로토콜 추상 클래스."""

    def __init__(self, node: 'Node'):
        self.node = node
        self.routing_table: Dict[int, int] = {}  # destination -> next_hop
        self.sequence_number: int = 0

        # 통계
        self.control_packets_sent: int = 0
        self.control_packets_received: int = 0
        self.route_discoveries: int = 0
        self.route_failures: int = 0

    @property
    @abstractmethod
    def name(self) -> str:
        """프로토콜 이름."""
        pass

    @abstractmethod
    def initialize(self) -> None:
        """프로토콜 초기화."""
        pass

    @abstractmethod
    def update(self, current_time: float) -> List['Packet']:
        """주기적 업데이트. 전송할 제어 패킷 반환."""
        pass

    @abstractmethod
    def handle_packet(self, packet: 'Packet') -> Optional['Packet']:
        """패킷 처리. 포워딩할 패킷 반환 또는 None."""
        pass

    @abstractmethod
    def get_next_hop(self, destination_id: int) -> Optional[int]:
        """목적지까지의 다음 홉 노드 ID."""
        pass

    def get_routing_overhead(self) -> int:
        """라우팅 오버헤드 (제어 패킷 수)."""
        return self.control_packets_sent
