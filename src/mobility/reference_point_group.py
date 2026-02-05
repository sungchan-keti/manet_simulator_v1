"""Reference Point Group Mobility 모델."""
import random
import math
from typing import Dict, List
from dataclasses import dataclass

from .base import MobilityModel
from ..core.node import Node
from ..core.position import Position


@dataclass
class GroupInfo:
    """그룹 정보."""
    leader_id: int
    center: Position
    velocity: tuple  # (vx, vy, vz)
    members: List[int]


@dataclass
class MemberState:
    """멤버 노드 상태."""
    group_id: int
    offset: Position  # 그룹 중심으로부터의 오프셋


class ReferencePointGroupModel(MobilityModel):
    """Reference Point Group Mobility 모델.

    그룹 단위 이동. 그룹 리더를 중심으로 멤버들이 함께 이동.
    군집 이동하는 UGV/UAV 편대에 적합.
    """

    def __init__(self, area_width: float, area_height: float,
                 area_depth: float = 100.0,
                 max_group_speed: float = 15.0,
                 max_member_deviation: float = 30.0):
        super().__init__(area_width, area_height, area_depth)
        self.max_group_speed = max_group_speed
        self.max_member_deviation = max_member_deviation
        self.groups: Dict[int, GroupInfo] = {}
        self.member_states: Dict[int, MemberState] = {}

    @property
    def name(self) -> str:
        return "ReferencePointGroup"

    def create_group(self, group_id: int, leader: Node,
                     members: List[Node]) -> None:
        """그룹 생성."""
        self.groups[group_id] = GroupInfo(
            leader_id=leader.node_id,
            center=leader.position,
            velocity=(
                random.uniform(-self.max_group_speed, self.max_group_speed),
                random.uniform(-self.max_group_speed, self.max_group_speed),
                random.uniform(-self.max_group_speed / 2, self.max_group_speed / 2)
            ),
            members=[m.node_id for m in members]
        )

        for member in members:
            offset = Position(
                random.uniform(-self.max_member_deviation, self.max_member_deviation),
                random.uniform(-self.max_member_deviation, self.max_member_deviation),
                random.uniform(-self.max_member_deviation / 2, self.max_member_deviation / 2)
            )
            self.member_states[member.node_id] = MemberState(
                group_id=group_id,
                offset=offset
            )

    def update_position(self, node: Node, delta_time: float) -> Position:
        """노드 위치 업데이트."""
        if node.node_id not in self.member_states:
            # 그룹에 속하지 않은 노드는 정적
            return node.position

        state = self.member_states[node.node_id]
        group = self.groups.get(state.group_id)
        if not group:
            return node.position

        # 그룹 리더인 경우 그룹 중심 이동
        if node.node_id == group.leader_id:
            self._update_group_center(group, delta_time)

        # 멤버 오프셋에 랜덤 변동 추가
        offset_change = Position(
            random.gauss(0, 1) * delta_time,
            random.gauss(0, 1) * delta_time,
            random.gauss(0, 0.5) * delta_time
        )
        new_offset = state.offset + offset_change

        # 오프셋 제한
        dist = math.sqrt(new_offset.x**2 + new_offset.y**2 + new_offset.z**2)
        if dist > self.max_member_deviation:
            scale = self.max_member_deviation / dist
            new_offset = Position(
                new_offset.x * scale,
                new_offset.y * scale,
                new_offset.z * scale
            )
        state.offset = new_offset

        # 새 위치 계산
        new_pos = group.center + state.offset
        x, y, z = self._clamp_to_area(new_pos.x, new_pos.y, new_pos.z)
        node.position = Position(x, y, z)

        return node.position

    def _update_group_center(self, group: GroupInfo, delta_time: float) -> None:
        """그룹 중심 업데이트."""
        vx, vy, vz = group.velocity

        new_x = group.center.x + vx * delta_time
        new_y = group.center.y + vy * delta_time
        new_z = group.center.z + vz * delta_time

        # 경계 반사
        if new_x < 0 or new_x > self.area_width:
            vx = -vx
            new_x = max(0, min(new_x, self.area_width))
        if new_y < 0 or new_y > self.area_height:
            vy = -vy
            new_y = max(0, min(new_y, self.area_height))
        if new_z < 0 or new_z > self.area_depth:
            vz = -vz
            new_z = max(0, min(new_z, self.area_depth))

        group.center = Position(new_x, new_y, new_z)
        group.velocity = (vx, vy, vz)

        # 속도에 약간의 랜덤 변동
        group.velocity = (
            vx + random.gauss(0, 0.5),
            vy + random.gauss(0, 0.5),
            vz + random.gauss(0, 0.25)
        )
