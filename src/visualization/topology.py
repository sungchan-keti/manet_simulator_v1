"""네트워크 토폴로지 시각화 모듈."""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.collections import LineCollection
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Line3DCollection
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.network import Network
    from ..core.node import Node


class TopologyVisualizer:
    """네트워크 토폴로지 시각화."""

    # 노드 타입별 색상
    NODE_COLORS = {
        'gcs': '#FF4444',   # 빨강 - GCS
        'ugv': '#4444FF',   # 파랑 - UGV
        'uav': '#44FF44',   # 초록 - UAV
    }

    # 노드 타입별 마커
    NODE_MARKERS = {
        'gcs': 's',  # 사각형
        'ugv': 'o',  # 원
        'uav': '^',  # 삼각형
    }

    def __init__(self, output_dir: str = "results/topology"):
        """초기화.

        Args:
            output_dir: 이미지 저장 디렉토리
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.frame_count = 0

    def capture_topology(
        self,
        network: 'Network',
        current_time: float,
        protocol_name: str = "",
        show_links: bool = True,
        show_range: bool = False,
        title_suffix: str = ""
    ) -> str:
        """현재 토폴로지를 이미지로 저장.

        Args:
            network: 네트워크 객체
            current_time: 현재 시뮬레이션 시간
            protocol_name: 프로토콜 이름
            show_links: 링크 표시 여부
            show_range: 전송 범위 표시 여부
            title_suffix: 제목 접미사

        Returns:
            저장된 파일 경로
        """
        fig, ax = plt.subplots(1, 1, figsize=(10, 10))

        nodes = list(network.nodes.values())
        if not nodes:
            plt.close(fig)
            return ""

        # 링크 그리기
        if show_links:
            self._draw_links(ax, nodes)

        # 전송 범위 그리기
        if show_range:
            self._draw_transmission_range(ax, nodes)

        # 노드 그리기
        self._draw_nodes(ax, nodes)

        # 축 설정
        self._setup_axes(ax, nodes)

        # 제목 설정
        title = f"Network Topology - {protocol_name}" if protocol_name else "Network Topology"
        title += f" (t={current_time:.1f}s)"
        if title_suffix:
            title += f" {title_suffix}"
        ax.set_title(title, fontsize=14, fontweight='bold')

        # 범례 추가
        self._add_legend(ax)

        # 파일 저장
        filename = f"topology_{protocol_name.lower()}_{self.frame_count:04d}.png"
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)

        self.frame_count += 1
        return str(filepath)

    def _draw_nodes(self, ax, nodes: List['Node']) -> None:
        """노드 그리기."""
        for node in nodes:
            node_type = node.node_type.value
            color = self.NODE_COLORS.get(node_type, '#888888')
            marker = self.NODE_MARKERS.get(node_type, 'o')
            size = 150 if node_type == 'gcs' else 100

            ax.scatter(
                node.position.x,
                node.position.y,
                c=color,
                marker=marker,
                s=size,
                edgecolors='black',
                linewidths=1,
                zorder=3
            )

            # 노드 ID 라벨
            ax.annotate(
                str(node.node_id),
                (node.position.x, node.position.y),
                xytext=(5, 5),
                textcoords='offset points',
                fontsize=8,
                fontweight='bold',
                zorder=4
            )

    def _draw_links(self, ax, nodes: List['Node']) -> None:
        """링크 그리기."""
        lines = []
        colors = []

        drawn_links = set()
        for node in nodes:
            for neighbor_id in node.neighbors:
                # 중복 링크 방지
                link_key = tuple(sorted([node.node_id, neighbor_id]))
                if link_key in drawn_links:
                    continue
                drawn_links.add(link_key)

                # 이웃 노드 찾기
                neighbor = None
                for n in nodes:
                    if n.node_id == neighbor_id:
                        neighbor = n
                        break

                if neighbor:
                    lines.append([
                        (node.position.x, node.position.y),
                        (neighbor.position.x, neighbor.position.y)
                    ])
                    colors.append('#AAAAAA')

        if lines:
            lc = LineCollection(lines, colors=colors, linewidths=0.8, alpha=0.6, zorder=1)
            ax.add_collection(lc)

    def _draw_transmission_range(self, ax, nodes: List['Node']) -> None:
        """전송 범위 원 그리기."""
        for node in nodes:
            circle = plt.Circle(
                (node.position.x, node.position.y),
                node.transmission_range,
                fill=False,
                color='gray',
                linestyle='--',
                linewidth=0.5,
                alpha=0.3,
                zorder=0
            )
            ax.add_patch(circle)

    def _setup_axes(self, ax, nodes: List['Node']) -> None:
        """축 설정."""
        # 경계 계산
        xs = [n.position.x for n in nodes]
        ys = [n.position.y for n in nodes]

        margin = 50
        x_min, x_max = min(xs) - margin, max(xs) + margin
        y_min, y_max = min(ys) - margin, max(ys) + margin

        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_min, y_max)
        ax.set_xlabel('X (m)', fontsize=10)
        ax.set_ylabel('Y (m)', fontsize=10)
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)

    def _add_legend(self, ax) -> None:
        """범례 추가."""
        legend_elements = [
            mpatches.Patch(color=self.NODE_COLORS['gcs'], label='GCS'),
            mpatches.Patch(color=self.NODE_COLORS['ugv'], label='UGV'),
            mpatches.Patch(color=self.NODE_COLORS['uav'], label='UAV'),
            plt.Line2D([0], [0], color='#AAAAAA', linewidth=1, label='Link'),
        ]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=9)

    def create_animation_frames(
        self,
        network: 'Network',
        times: List[float],
        protocol_name: str = ""
    ) -> List[str]:
        """여러 시점의 토폴로지를 연속 프레임으로 저장.

        Args:
            network: 네트워크 객체
            times: 캡처할 시간 목록
            protocol_name: 프로토콜 이름

        Returns:
            저장된 파일 경로 목록
        """
        filepaths = []
        for t in times:
            filepath = self.capture_topology(network, t, protocol_name)
            filepaths.append(filepath)
        return filepaths

    def reset(self) -> None:
        """프레임 카운터 리셋."""
        self.frame_count = 0

    def capture_topology_3d(
        self,
        network: 'Network',
        current_time: float,
        protocol_name: str = "",
        show_links: bool = True,
        show_ground: bool = True,
        title_suffix: str = "",
        elev: float = 25,
        azim: float = 45
    ) -> str:
        """현재 토폴로지를 3D 이미지로 저장.

        Args:
            network: 네트워크 객체
            current_time: 현재 시뮬레이션 시간
            protocol_name: 프로토콜 이름
            show_links: 링크 표시 여부
            show_ground: 지면 그리드 표시 여부
            title_suffix: 제목 접미사
            elev: 시점 고도각 (도)
            azim: 시점 방위각 (도)

        Returns:
            저장된 파일 경로
        """
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')

        nodes = list(network.nodes.values())
        if not nodes:
            plt.close(fig)
            return ""

        # 지면 그리드 그리기
        if show_ground:
            self._draw_ground_grid_3d(ax, nodes)

        # 링크 그리기
        if show_links:
            self._draw_links_3d(ax, nodes)

        # 노드 그리기
        self._draw_nodes_3d(ax, nodes)

        # 고도선 그리기 (UAV와 지면 연결)
        self._draw_altitude_lines(ax, nodes)

        # 축 설정
        self._setup_axes_3d(ax, nodes)

        # 시점 설정
        ax.view_init(elev=elev, azim=azim)

        # 제목 설정
        title = f"3D Network Topology - {protocol_name}" if protocol_name else "3D Network Topology"
        title += f" (t={current_time:.1f}s)"
        if title_suffix:
            title += f" {title_suffix}"
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)

        # 범례 추가
        self._add_legend_3d(ax)

        # 파일 저장
        filename = f"topology_3d_{protocol_name.lower()}_{self.frame_count:04d}.png"
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)

        self.frame_count += 1
        return str(filepath)

    def _draw_nodes_3d(self, ax, nodes: List['Node']) -> None:
        """3D 노드 그리기."""
        for node in nodes:
            node_type = node.node_type.value
            color = self.NODE_COLORS.get(node_type, '#888888')
            marker = self.NODE_MARKERS.get(node_type, 'o')
            size = 200 if node_type == 'gcs' else 150 if node_type == 'uav' else 120

            ax.scatter(
                node.position.x,
                node.position.y,
                node.position.z,
                c=color,
                marker=marker,
                s=size,
                edgecolors='black',
                linewidths=1,
                depthshade=True,
                zorder=3
            )

            # 노드 ID 라벨
            ax.text(
                node.position.x + 10,
                node.position.y + 10,
                node.position.z + 5,
                str(node.node_id),
                fontsize=9,
                fontweight='bold',
                zorder=4
            )

    def _draw_links_3d(self, ax, nodes: List['Node']) -> None:
        """3D 링크 그리기."""
        drawn_links = set()
        node_dict = {n.node_id: n for n in nodes}

        for node in nodes:
            for neighbor_id in node.neighbors:
                # 중복 링크 방지
                link_key = tuple(sorted([node.node_id, neighbor_id]))
                if link_key in drawn_links:
                    continue
                drawn_links.add(link_key)

                neighbor = node_dict.get(neighbor_id)
                if neighbor:
                    # 링크 색상: 지상-지상=파랑, 공중-공중=초록, 지상-공중=주황
                    if node.position.z == 0 and neighbor.position.z == 0:
                        color = '#6666FF'  # 지상 링크
                        alpha = 0.5
                    elif node.position.z > 0 and neighbor.position.z > 0:
                        color = '#66FF66'  # 공중 링크
                        alpha = 0.6
                    else:
                        color = '#FFAA44'  # 지상-공중 링크
                        alpha = 0.7

                    ax.plot(
                        [node.position.x, neighbor.position.x],
                        [node.position.y, neighbor.position.y],
                        [node.position.z, neighbor.position.z],
                        color=color,
                        linewidth=1.2,
                        alpha=alpha,
                        zorder=1
                    )

    def _draw_altitude_lines(self, ax, nodes: List['Node']) -> None:
        """고도선 그리기 (UAV와 지면 연결)."""
        for node in nodes:
            if node.position.z > 0:  # UAV만
                ax.plot(
                    [node.position.x, node.position.x],
                    [node.position.y, node.position.y],
                    [0, node.position.z],
                    color='gray',
                    linewidth=0.8,
                    linestyle=':',
                    alpha=0.5,
                    zorder=0
                )
                # 지면에 그림자 점
                ax.scatter(
                    node.position.x,
                    node.position.y,
                    0,
                    c='gray',
                    marker='x',
                    s=30,
                    alpha=0.3,
                    zorder=0
                )

    def _draw_ground_grid_3d(self, ax, nodes: List['Node']) -> None:
        """지면 그리드 그리기."""
        xs = [n.position.x for n in nodes]
        ys = [n.position.y for n in nodes]

        margin = 50
        x_min, x_max = min(xs) - margin, max(xs) + margin
        y_min, y_max = min(ys) - margin, max(ys) + margin

        # 지면 그리드
        grid_step = 100
        x_grid = np.arange(x_min, x_max + grid_step, grid_step)
        y_grid = np.arange(y_min, y_max + grid_step, grid_step)

        for x in x_grid:
            ax.plot([x, x], [y_min, y_max], [0, 0],
                    color='lightgray', linewidth=0.5, alpha=0.5)
        for y in y_grid:
            ax.plot([x_min, x_max], [y, y], [0, 0],
                    color='lightgray', linewidth=0.5, alpha=0.5)

    def _setup_axes_3d(self, ax, nodes: List['Node']) -> None:
        """3D 축 설정."""
        xs = [n.position.x for n in nodes]
        ys = [n.position.y for n in nodes]
        zs = [n.position.z for n in nodes]

        margin = 50
        x_min, x_max = min(xs) - margin, max(xs) + margin
        y_min, y_max = min(ys) - margin, max(ys) + margin
        z_max = max(zs) + 30 if max(zs) > 0 else 100

        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_min, y_max)
        ax.set_zlim(0, z_max)

        ax.set_xlabel('X (m)', fontsize=10, labelpad=10)
        ax.set_ylabel('Y (m)', fontsize=10, labelpad=10)
        ax.set_zlabel('Z - Altitude (m)', fontsize=10, labelpad=10)

        # 배경색 설정
        ax.xaxis.pane.fill = False
        ax.yaxis.pane.fill = False
        ax.zaxis.pane.fill = False
        ax.xaxis.pane.set_edgecolor('lightgray')
        ax.yaxis.pane.set_edgecolor('lightgray')
        ax.zaxis.pane.set_edgecolor('lightgray')

    def _add_legend_3d(self, ax) -> None:
        """3D 범례 추가."""
        legend_elements = [
            plt.Line2D([0], [0], marker='s', color='w', markerfacecolor=self.NODE_COLORS['gcs'],
                       markersize=10, label='GCS (Ground)'),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=self.NODE_COLORS['ugv'],
                       markersize=10, label='UGV (Ground)'),
            plt.Line2D([0], [0], marker='^', color='w', markerfacecolor=self.NODE_COLORS['uav'],
                       markersize=10, label='UAV (Aerial)'),
            plt.Line2D([0], [0], color='#6666FF', linewidth=2, label='Ground Link'),
            plt.Line2D([0], [0], color='#66FF66', linewidth=2, label='Aerial Link'),
            plt.Line2D([0], [0], color='#FFAA44', linewidth=2, label='Ground-Air Link'),
        ]
        ax.legend(handles=legend_elements, loc='upper left', fontsize=8)
