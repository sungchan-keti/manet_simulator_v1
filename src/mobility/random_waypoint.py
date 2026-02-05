"""Random Waypoint 이동성 모델."""
import random
import math
from typing import Dict
from dataclasses import dataclass

from .base import MobilityModel
from ..core.node import Node
from ..core.position import Position


@dataclass
class WaypointState:
    """노드별 waypoint 상태."""
    destination: Position
    speed: float
    pause_remaining: float


class RandomWaypointModel(MobilityModel):
    """Random Waypoint 이동성 모델.

    노드가 랜덤 목적지로 이동 후 일정 시간 대기를 반복.
    UGV에 적합한 기본 이동 모델.
    """

    def __init__(self, area_width: float, area_height: float,
                 min_speed: float = 1.0, max_speed: float = 10.0,
                 max_pause: float = 5.0):
        super().__init__(area_width, area_height)
        self.min_speed = min_speed
        self.max_speed = max_speed
        self.max_pause = max_pause
        self.node_states: Dict[int, WaypointState] = {}

    @property
    def name(self) -> str:
        return "RandomWaypoint"

    def update_position(self, node: Node, delta_time: float) -> Position:
        """노드 위치 업데이트."""
        if node.node_id not in self.node_states:
            self._init_node_state(node)

        state = self.node_states[node.node_id]

        # 대기 중
        if state.pause_remaining > 0:
            state.pause_remaining -= delta_time
            return node.position

        # 목적지까지 거리
        dist_to_dest = node.position.distance_to(state.destination)
        move_dist = state.speed * delta_time

        # 목적지 도착
        if move_dist >= dist_to_dest:
            node.position = state.destination
            self._set_new_destination(node, state)
            return node.position

        # 이동
        dx = state.destination.x - node.position.x
        dy = state.destination.y - node.position.y
        dist = math.sqrt(dx * dx + dy * dy)

        if dist > 0:
            ratio = move_dist / dist
            new_x = node.position.x + dx * ratio
            new_y = node.position.y + dy * ratio
            node.position = Position(new_x, new_y, node.position.z)

        return node.position

    def _init_node_state(self, node: Node) -> None:
        """노드 상태 초기화."""
        dest = Position(
            random.uniform(0, self.area_width),
            random.uniform(0, self.area_height),
            0.0
        )
        self.node_states[node.node_id] = WaypointState(
            destination=dest,
            speed=random.uniform(self.min_speed, self.max_speed),
            pause_remaining=0.0
        )

    def _set_new_destination(self, node: Node, state: WaypointState) -> None:
        """새로운 목적지 설정."""
        state.destination = Position(
            random.uniform(0, self.area_width),
            random.uniform(0, self.area_height),
            0.0
        )
        state.speed = random.uniform(self.min_speed, self.max_speed)
        state.pause_remaining = random.uniform(0, self.max_pause)
