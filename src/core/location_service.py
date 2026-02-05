"""Shared location service for geographic routing protocols.

This module provides a centralized location service that maintains node positions,
eliminating the O(n^2) per-step update where every node copies every other node's
position into its own dictionary.

All GPSR protocol instances can reference this single shared service instead of
maintaining their own copy of all node locations.
"""
from typing import Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .position import Position


class LocationService:
    """Shared location service for all nodes.

    This is a singleton-like service that maintains a single dictionary of all
    node positions. GPSR protocol instances query this service rather than
    maintaining their own per-node dictionaries.

    Performance improvement:
    - Before: O(n^2) per step (n nodes each updating n positions)
    - After: O(n) per step (updating n positions once in shared service)
    """

    def __init__(self):
        # Single dictionary shared by all GPSR instances
        self._positions: Dict[int, 'Position'] = {}

    def update_position(self, node_id: int, position: 'Position') -> None:
        """Update a node's position in the service.

        Args:
            node_id: The node's identifier
            position: The node's current position
        """
        self._positions[node_id] = position

    def get_position(self, node_id: int) -> Optional['Position']:
        """Get a node's position.

        Args:
            node_id: The node's identifier

        Returns:
            The node's position, or None if not registered
        """
        return self._positions.get(node_id)

    def remove_node(self, node_id: int) -> None:
        """Remove a node from the service."""
        self._positions.pop(node_id, None)

    def clear(self) -> None:
        """Clear all positions."""
        self._positions.clear()

    def __contains__(self, node_id: int) -> bool:
        """Check if a node is registered."""
        return node_id in self._positions
