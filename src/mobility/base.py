"""이동성 모델 기본 클래스."""
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.node import Node
    from ..core.position import Position


class MobilityModel(ABC):
    """이동성 모델 추상 클래스."""

    def __init__(self, area_width: float, area_height: float,
                 area_depth: float = 0.0):
        """
        Args:
            area_width: 시뮬레이션 영역 너비 (m)
            area_height: 시뮬레이션 영역 높이 (m)
            area_depth: 시뮬레이션 영역 깊이/고도 (m), UAV용
        """
        self.area_width = area_width
        self.area_height = area_height
        self.area_depth = area_depth

    @property
    @abstractmethod
    def name(self) -> str:
        """모델 이름."""
        pass

    @abstractmethod
    def update_position(self, node: 'Node', delta_time: float) -> 'Position':
        """노드 위치 업데이트.

        Args:
            node: 업데이트할 노드
            delta_time: 경과 시간 (초)

        Returns:
            새로운 위치
        """
        pass

    def _clamp_to_area(self, x: float, y: float, z: float) -> tuple:
        """위치를 시뮬레이션 영역 내로 제한."""
        x = max(0, min(x, self.area_width))
        y = max(0, min(y, self.area_height))
        z = max(0, min(z, self.area_depth)) if self.area_depth > 0 else z
        return x, y, z
