"""시뮬레이션 시나리오 정의."""
from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class Scenario:
    """시뮬레이션 시나리오 설정."""

    # 기본 설정
    name: str = "default"
    duration: float = 100.0  # 시뮬레이션 시간 (초)
    time_step: float = 0.1   # 시간 간격 (초)

    # 영역 설정
    area_width: float = 1000.0   # 미터
    area_height: float = 1000.0  # 미터
    area_depth: float = 200.0    # 미터 (UAV 고도)

    # 노드 설정
    num_gcs: int = 1          # GCS (Ground Control Station) 수
    num_ugv: int = 10
    num_uav: int = 5
    transmission_range: float = 250.0  # 미터

    # GCS 위치 설정
    gcs_position: Tuple[float, float, float] = None  # (x, y, z), None이면 중앙

    # 이동성 설정
    mobility_model: str = "random_waypoint"
    min_speed: float = 1.0   # m/s
    max_speed: float = 20.0  # m/s

    # 트래픽 설정
    traffic_type: str = "cbr"  # cbr, poisson
    traffic_mode: str = "gcs"  # gcs: 모든 노드↔GCS, random: 임의 쌍
    packet_rate: float = 10.0  # packets/second
    packet_size: int = 512     # bytes
    traffic_pairs: List[Tuple[int, int]] = field(default_factory=list)

    # 프로토콜 설정
    protocol: str = "olsr"  # olsr, aodv, gpsr

    def __post_init__(self):
        # GCS 위치 기본값: 영역 중앙
        if self.gcs_position is None:
            self.gcs_position = (self.area_width / 2, self.area_height / 2, 0.0)

        if not self.traffic_pairs:
            if self.traffic_mode == "gcs":
                # 모든 UGV/UAV가 GCS(노드 0)와 통신
                # GCS는 노드 ID 0
                gcs_id = 0
                for i in range(1, self.num_gcs + self.num_ugv + self.num_uav):
                    self.traffic_pairs.append((i, gcs_id))  # 노드→GCS
            else:
                # 기존 방식: 임의 쌍
                total_nodes = self.num_gcs + self.num_ugv + self.num_uav
                if total_nodes >= 2:
                    mid = total_nodes // 2
                    self.traffic_pairs = [(i, mid + i) for i in range(min(3, mid))]
