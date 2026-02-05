"""Core 모듈 테스트."""
import pytest

from src.core.position import Position
from src.core.node import Node, NodeType
from src.core.packet import Packet, PacketType
from src.core.network import Network


class TestPosition:
    def test_distance_calculation(self):
        p1 = Position(0, 0, 0)
        p2 = Position(3, 4, 0)
        assert p1.distance_to(p2) == 5.0

    def test_3d_distance(self):
        p1 = Position(0, 0, 0)
        p2 = Position(1, 2, 2)
        assert p1.distance_to(p2) == 3.0

    def test_position_addition(self):
        p1 = Position(1, 2, 3)
        p2 = Position(4, 5, 6)
        result = p1 + p2
        assert result.x == 5
        assert result.y == 7
        assert result.z == 9


class TestNode:
    def test_node_creation(self):
        node = Node(
            node_id=1,
            node_type=NodeType.UGV,
            position=Position(0, 0, 0)
        )
        assert node.node_id == 1
        assert node.is_active is True

    def test_in_range_check(self):
        node1 = Node(0, NodeType.UGV, Position(0, 0, 0), transmission_range=100)
        node2 = Node(1, NodeType.UGV, Position(50, 0, 0))
        node3 = Node(2, NodeType.UGV, Position(200, 0, 0))

        assert node1.is_in_range(node2) is True
        assert node1.is_in_range(node3) is False

    def test_energy_consumption(self):
        node = Node(0, NodeType.UAV, Position(0, 0, 50))
        initial_energy = node.node_energy.current_energy

        # Consume idle energy
        node.consume_idle_energy(1.0)
        assert node.node_energy.current_energy < initial_energy
        assert node.is_active is True

        # Deplete energy by consuming a large amount
        node.node_energy.current_energy = 0.01
        node.consume_idle_energy(1.0)
        assert node.is_active is False


class TestPacket:
    def test_packet_creation(self):
        packet = Packet(
            packet_id=1,
            packet_type=PacketType.DATA,
            source_id=0,
            destination_id=5,
            payload=b"test"
        )
        assert packet.packet_id == 1
        assert packet.hop_count == 0

    def test_packet_size(self):
        packet = Packet(
            packet_id=1,
            packet_type=PacketType.DATA,
            source_id=0,
            destination_id=5,
            payload=b"x" * 100
        )
        assert packet.size == 140  # 40 header + 100 payload


class TestNetwork:
    def test_add_remove_node(self):
        network = Network()
        node = Node(0, NodeType.UGV, Position(0, 0, 0))

        network.add_node(node)
        assert network.get_node(0) is not None

        network.remove_node(0)
        assert network.get_node(0) is None

    def test_topology_update(self):
        network = Network()
        node1 = Node(0, NodeType.UGV, Position(0, 0, 0), transmission_range=100)
        node2 = Node(1, NodeType.UGV, Position(50, 0, 0), transmission_range=100)
        node3 = Node(2, NodeType.UGV, Position(200, 0, 0), transmission_range=100)

        network.add_node(node1)
        network.add_node(node2)
        network.add_node(node3)
        network.update_topology()

        neighbors = network.get_neighbors(0)
        assert 1 in neighbors
        assert 2 not in neighbors

    def test_connectivity(self):
        network = Network()
        # 연결된 네트워크
        for i in range(3):
            network.add_node(Node(i, NodeType.UGV, Position(i * 50, 0, 0), transmission_range=100))
        network.update_topology()
        assert network.is_connected() is True
