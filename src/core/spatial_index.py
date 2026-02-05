"""Spatial indexing for efficient neighbor discovery.

This module provides a grid-based spatial index to reduce neighbor discovery
complexity from O(n^2) to approximately O(n) for uniformly distributed nodes.
"""
from typing import Dict, List, Set, Tuple, TYPE_CHECKING
from collections import defaultdict
import math

if TYPE_CHECKING:
    from .node import Node


class SpatialGrid:
    """Grid-based spatial index for efficient neighbor queries.

    Divides the simulation area into cells of size equal to the transmission range.
    Nodes in the same or adjacent cells are potential neighbors.

    Time complexity:
    - Update: O(1) per node
    - Query: O(k) where k is the average number of nodes in nearby cells
    - Total topology update: O(n * k) instead of O(n^2)
    """

    def __init__(self, cell_size: float):
        """Initialize spatial grid.

        Args:
            cell_size: Size of each grid cell (typically transmission_range)
        """
        self.cell_size = cell_size
        # Map from cell coordinates to set of node IDs in that cell
        self._grid: Dict[Tuple[int, int, int], Set[int]] = defaultdict(set)
        # Map from node ID to its current cell
        self._node_cells: Dict[int, Tuple[int, int, int]] = {}

    def _get_cell(self, x: float, y: float, z: float) -> Tuple[int, int, int]:
        """Get the cell coordinates for a position."""
        return (
            int(math.floor(x / self.cell_size)),
            int(math.floor(y / self.cell_size)),
            int(math.floor(z / self.cell_size))
        )

    def update_node(self, node_id: int, x: float, y: float, z: float) -> None:
        """Update a node's position in the grid.

        Args:
            node_id: The node's identifier
            x, y, z: The node's position coordinates
        """
        new_cell = self._get_cell(x, y, z)

        # Remove from old cell if exists
        if node_id in self._node_cells:
            old_cell = self._node_cells[node_id]
            if old_cell != new_cell:
                self._grid[old_cell].discard(node_id)
                if not self._grid[old_cell]:
                    del self._grid[old_cell]

        # Add to new cell
        self._grid[new_cell].add(node_id)
        self._node_cells[node_id] = new_cell

    def remove_node(self, node_id: int) -> None:
        """Remove a node from the grid."""
        if node_id in self._node_cells:
            cell = self._node_cells[node_id]
            self._grid[cell].discard(node_id)
            if not self._grid[cell]:
                del self._grid[cell]
            del self._node_cells[node_id]

    def get_nearby_node_ids(self, x: float, y: float, z: float) -> Set[int]:
        """Get IDs of nodes in the same or adjacent cells.

        Returns nodes that are potential neighbors (within 1 cell distance).
        The actual distance check should still be performed by the caller.

        Args:
            x, y, z: Position to query around

        Returns:
            Set of node IDs that might be within transmission range
        """
        center_cell = self._get_cell(x, y, z)
        nearby = set()

        # Check 3x3x3 cube of cells around the center (27 cells total)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    cell = (
                        center_cell[0] + dx,
                        center_cell[1] + dy,
                        center_cell[2] + dz
                    )
                    nearby.update(self._grid.get(cell, set()))

        return nearby

    def clear(self) -> None:
        """Clear all nodes from the grid."""
        self._grid.clear()
        self._node_cells.clear()
