"""패킷 정의 모듈."""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
import time


class PacketType(Enum):
    """패킷 유형."""
    DATA = "data"
    HELLO = "hello"           # OLSR/AODV
    TC = "tc"                 # OLSR Topology Control
    RREQ = "rreq"             # AODV Route Request
    RREP = "rrep"             # AODV Route Reply
    RERR = "rerr"             # AODV Route Error
    BEACON = "beacon"         # GPSR 위치 브로드캐스트


@dataclass
class Packet:
    """네트워크 패킷."""
    packet_id: int
    packet_type: PacketType
    source_id: int
    destination_id: int
    payload: bytes = b""
    ttl: int = 64
    hop_count: int = 0
    created_at: float = field(default_factory=time.time)
    path: List[int] = field(default_factory=list)
    sequence_number: int = 0

    # AODV 관련 필드
    broadcast_id: int = 0
    dest_sequence: int = 0

    # GPSR 관련 필드
    destination_position: Optional[tuple] = None
    mode: str = "greedy"  # greedy or perimeter

    # 지연 측정 필드
    route_discovery_started: Optional[float] = None  # 경로 탐색 시작 시간
    first_hop_time: Optional[float] = None           # 첫 홉 전송 시간 (경로 확보 후)

    def __post_init__(self):
        if self.path is None:
            self.path = []

    @property
    def size(self) -> int:
        """패킷 크기 (bytes)."""
        header_size = 40  # 기본 헤더 크기
        return header_size + len(self.payload)

    def copy(self) -> 'Packet':
        """Create a shallow copy of the packet with a new path list.

        This is more efficient than deepcopy() because:
        - Immutable fields (int, float, bytes, tuple, Enum) are shared
        - Only the mutable 'path' list is copied

        Performance: ~10x faster than copy.deepcopy() for typical packets.
        """
        return Packet(
            packet_id=self.packet_id,
            packet_type=self.packet_type,
            source_id=self.source_id,
            destination_id=self.destination_id,
            payload=self.payload,  # bytes is immutable, safe to share
            ttl=self.ttl,
            hop_count=self.hop_count,
            created_at=self.created_at,
            path=self.path.copy(),  # Only mutable field that needs copying
            sequence_number=self.sequence_number,
            broadcast_id=self.broadcast_id,
            dest_sequence=self.dest_sequence,
            destination_position=self.destination_position,  # tuple is immutable
            mode=self.mode,
            route_discovery_started=self.route_discovery_started,
            first_hop_time=self.first_hop_time,
        )
