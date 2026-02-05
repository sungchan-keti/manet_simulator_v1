"""위치 및 거리 계산 모듈."""
from dataclasses import dataclass
import math


@dataclass
class Position:
    """3D 위치 좌표."""
    x: float
    y: float
    z: float = 0.0  # UAV의 고도

    def distance_to(self, other: 'Position') -> float:
        """다른 위치까지의 유클리드 거리."""
        return math.sqrt(
            (self.x - other.x) ** 2 +
            (self.y - other.y) ** 2 +
            (self.z - other.z) ** 2
        )

    def __add__(self, other: 'Position') -> 'Position':
        return Position(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: 'Position') -> 'Position':
        return Position(self.x - other.x, self.y - other.y, self.z - other.z)
