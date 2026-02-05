"""Gauss-Markov 이동성 모델."""
import random
import math
from typing import Dict
from dataclasses import dataclass

from .base import MobilityModel
from ..core.node import Node
from ..core.position import Position


@dataclass
class GaussMarkovState:
    """노드별 Gauss-Markov 상태."""
    speed: float
    direction: float  # radians (xy plane)
    pitch: float      # radians (z direction)


class GaussMarkovModel(MobilityModel):
    """Gauss-Markov 이동성 모델.

    시간 상관성이 있는 부드러운 이동 패턴.
    UAV의 자연스러운 비행 경로에 적합.
    """

    def __init__(self, area_width: float, area_height: float,
                 area_depth: float = 200.0,
                 alpha: float = 0.75,
                 mean_speed: float = 15.0,
                 speed_std: float = 3.0):
        """
        Args:
            alpha: 메모리 계수 (0: 무작위, 1: 직진)
            mean_speed: 평균 속도 (m/s)
            speed_std: 속도 표준편차
        """
        super().__init__(area_width, area_height, area_depth)
        self.alpha = alpha
        self.mean_speed = mean_speed
        self.speed_std = speed_std
        self.node_states: Dict[int, GaussMarkovState] = {}

    @property
    def name(self) -> str:
        return "GaussMarkov"

    def update_position(self, node: Node, delta_time: float) -> Position:
        """노드 위치 업데이트."""
        if node.node_id not in self.node_states:
            self._init_node_state(node)

        state = self.node_states[node.node_id]

        # Gauss-Markov 속도/방향 업데이트
        alpha = self.alpha
        sqrt_1_alpha2 = math.sqrt(1 - alpha * alpha)

        state.speed = (
            alpha * state.speed +
            (1 - alpha) * self.mean_speed +
            sqrt_1_alpha2 * random.gauss(0, self.speed_std)
        )
        state.speed = max(0, state.speed)

        state.direction = (
            alpha * state.direction +
            (1 - alpha) * 0 +  # 평균 방향 0
            sqrt_1_alpha2 * random.gauss(0, math.pi / 6)
        )

        state.pitch = (
            alpha * state.pitch +
            (1 - alpha) * 0 +
            sqrt_1_alpha2 * random.gauss(0, math.pi / 12)
        )

        # 새 위치 계산
        vx = state.speed * math.cos(state.direction) * math.cos(state.pitch)
        vy = state.speed * math.sin(state.direction) * math.cos(state.pitch)
        vz = state.speed * math.sin(state.pitch)

        new_x = node.position.x + vx * delta_time
        new_y = node.position.y + vy * delta_time
        new_z = node.position.z + vz * delta_time

        # 경계 반사
        if new_x < 0 or new_x > self.area_width:
            state.direction = math.pi - state.direction
            new_x = max(0, min(new_x, self.area_width))
        if new_y < 0 or new_y > self.area_height:
            state.direction = -state.direction
            new_y = max(0, min(new_y, self.area_height))
        if new_z < 0 or new_z > self.area_depth:
            state.pitch = -state.pitch
            new_z = max(0, min(new_z, self.area_depth))

        node.position = Position(new_x, new_y, new_z)
        return node.position

    def _init_node_state(self, node: Node) -> None:
        """노드 상태 초기화."""
        self.node_states[node.node_id] = GaussMarkovState(
            speed=self.mean_speed,
            direction=random.uniform(0, 2 * math.pi),
            pitch=random.uniform(-math.pi / 6, math.pi / 6)
        )
