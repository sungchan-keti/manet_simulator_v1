"""네트워크 토폴로지 관리 모듈."""
from typing import Dict, List, Optional
import networkx as nx

from .node import Node
from .packet import Packet
from .spatial_index import SpatialGrid


class Network:
    """MANET 네트워크."""

    def __init__(self, transmission_range: float = 250.0):
        self.nodes: Dict[int, Node] = {}
        self.graph: nx.Graph = nx.Graph()
        self.time: float = 0.0

        # Spatial index for O(n) neighbor discovery instead of O(n^2)
        self._spatial_grid = SpatialGrid(cell_size=transmission_range)
        self._transmission_range = transmission_range

        # 통계
        self.total_packets_sent: int = 0
        self.total_packets_delivered: int = 0
        self.total_packets_dropped: int = 0

    def add_node(self, node: Node) -> None:
        """노드 추가."""
        self.nodes[node.node_id] = node
        self.graph.add_node(node.node_id, node=node)
        # Add to spatial index
        self._spatial_grid.update_node(
            node.node_id,
            node.position.x,
            node.position.y,
            node.position.z
        )

    def remove_node(self, node_id: int) -> None:
        """노드 제거."""
        if node_id in self.nodes:
            self._spatial_grid.remove_node(node_id)
            del self.nodes[node_id]
            self.graph.remove_node(node_id)

    def get_node(self, node_id: int) -> Optional[Node]:
        """노드 조회."""
        return self.nodes.get(node_id)

    def update_topology(self) -> None:
        """네트워크 토폴로지 갱신.

        Uses spatial indexing for O(n * k) complexity where k is the average
        number of nearby nodes, instead of O(n^2) for brute-force approach.
        """
        # 모든 엣지 제거 후 재구성
        self.graph.clear_edges()

        # Update spatial index positions for all nodes
        for node in self.nodes.values():
            self._spatial_grid.update_node(
                node.node_id,
                node.position.x,
                node.position.y,
                node.position.z
            )

        # Update neighbors using spatial index
        for node in self.nodes.values():
            # Get candidate neighbors from spatial index (nearby cells only)
            nearby_ids = self._spatial_grid.get_nearby_node_ids(
                node.position.x,
                node.position.y,
                node.position.z
            )

            # Update neighbors with filtered candidate list
            node.update_neighbors_from_candidates(nearby_ids, self.nodes)

            # Update graph edges
            for neighbor_id in node.neighbors:
                self.graph.add_edge(node.node_id, neighbor_id)

    def get_neighbors(self, node_id: int) -> List[int]:
        """노드의 이웃 목록."""
        if node_id in self.graph:
            return list(self.graph.neighbors(node_id))
        return []

    def is_connected(self) -> bool:
        """네트워크 연결성 확인."""
        if len(self.nodes) == 0:
            return True
        return nx.is_connected(self.graph)

    def get_shortest_path(self, source_id: int, dest_id: int) -> Optional[List[int]]:
        """최단 경로 (기준선 비교용)."""
        try:
            return nx.shortest_path(self.graph, source_id, dest_id)
        except nx.NetworkXNoPath:
            return None
