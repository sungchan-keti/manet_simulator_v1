"""프로토콜 테스트."""
import pytest

from src.core.node import Node, NodeType
from src.core.position import Position
from src.core.packet import Packet, PacketType
from src.protocols.olsr import OLSR
from src.protocols.aodv import AODV
from src.protocols.gpsr import GPSR


class TestOLSR:
    def test_initialization(self):
        node = Node(0, NodeType.UGV, Position(0, 0, 0))
        olsr = OLSR(node)
        olsr.initialize()

        assert olsr.name == "OLSR"
        assert len(olsr.neighbors) == 0
        assert len(olsr.mpr_set) == 0

    def test_hello_generation(self):
        node = Node(0, NodeType.UGV, Position(0, 0, 0))
        olsr = OLSR(node)
        olsr.initialize()

        # HELLO 간격 후 패킷 생성
        packets = olsr.update(OLSR.HELLO_INTERVAL + 0.1)
        assert len(packets) >= 1
        assert packets[0].packet_type == PacketType.HELLO


class TestAODV:
    def test_initialization(self):
        node = Node(0, NodeType.UGV, Position(0, 0, 0))
        aodv = AODV(node)
        aodv.initialize()

        assert aodv.name == "AODV"
        assert len(aodv.route_table) == 0

    def test_route_discovery(self):
        node = Node(0, NodeType.UGV, Position(0, 0, 0))
        aodv = AODV(node)
        aodv.initialize()

        rreq = aodv.discover_route(5)
        assert rreq.packet_type == PacketType.RREQ
        assert rreq.destination_id == 5
        assert rreq.source_id == 0


class TestGPSR:
    def test_initialization(self):
        node = Node(0, NodeType.UGV, Position(0, 0, 0))
        gpsr = GPSR(node)
        gpsr.initialize()

        assert gpsr.name == "GPSR"
        assert len(gpsr.neighbor_locations) == 0

    def test_beacon_generation(self):
        node = Node(0, NodeType.UGV, Position(100, 200, 0))
        gpsr = GPSR(node)
        gpsr.initialize()

        packets = gpsr.update(GPSR.BEACON_INTERVAL + 0.1)
        assert len(packets) == 1
        assert packets[0].packet_type == PacketType.BEACON

    def test_greedy_forwarding(self):
        node = Node(0, NodeType.UGV, Position(0, 0, 0))
        gpsr = GPSR(node)
        gpsr.initialize()

        # 이웃 등록
        gpsr.neighbor_locations[1] = type('obj', (object,), {
            'node_id': 1,
            'position': Position(50, 50, 0)
        })()
        gpsr.neighbor_locations[2] = type('obj', (object,), {
            'node_id': 2,
            'position': Position(80, 80, 0)
        })()

        # 목적지 (100, 100)에 가장 가까운 이웃 선택
        dest_pos = Position(100, 100, 0)
        next_hop = gpsr._greedy_next_hop(dest_pos)
        assert next_hop == 2  # 더 가까운 이웃
