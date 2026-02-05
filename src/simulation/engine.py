"""시뮬레이션 엔진."""
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Type

from .scenario import Scenario
from ..core.node import Node, NodeType
from ..core.network import Network
from ..core.packet import Packet, PacketType
from ..core.position import Position
from ..core.location_service import LocationService
from ..protocols.base import RoutingProtocol
from ..protocols.olsr import OLSR
from ..protocols.aodv import AODV
from ..protocols.gpsr import GPSR
from ..mobility.base import MobilityModel
from ..mobility.random_waypoint import RandomWaypointModel
from ..mobility.gauss_markov import GaussMarkovModel
from ..metrics.collector import MetricsCollector


@dataclass
class TrafficGenerator:
    """트래픽 생성기."""
    source_id: int
    dest_id: int
    packet_rate: float
    packet_size: int
    last_send_time: float = 0.0
    packet_counter: int = 0


class SimulationEngine:
    """MANET 시뮬레이션 엔진."""

    PROTOCOL_MAP: Dict[str, Type[RoutingProtocol]] = {
        "olsr": OLSR,
        "aodv": AODV,
        "gpsr": GPSR,
    }

    def __init__(self, scenario: Scenario):
        self.scenario = scenario
        self.network = Network(transmission_range=scenario.transmission_range)
        self.current_time = 0.0
        self.packet_id_counter = 0

        self.mobility_model: Optional[MobilityModel] = None
        self.traffic_generators: List[TrafficGenerator] = []
        self.pending_packets: List[Packet] = []
        self.pending_control_packets: List[tuple] = []  # (sender, packet) 튜플
        self.metrics = MetricsCollector()

        # Shared location service for GPSR (O(n) instead of O(n^2) updates)
        self._location_service: Optional[LocationService] = None
        if scenario.protocol.lower() == "gpsr":
            self._location_service = LocationService()
            GPSR.set_shared_location_service(self._location_service)

        self._setup()

    def _setup(self) -> None:
        """시뮬레이션 초기화."""
        self._create_nodes()
        self._setup_mobility()
        self._setup_protocols()
        self._setup_traffic()

    def _create_nodes(self) -> None:
        """노드 생성."""
        node_id = 0

        # GCS 생성 (노드 ID 0부터)
        for _ in range(self.scenario.num_gcs):
            gcs_pos = self.scenario.gcs_position
            pos = Position(gcs_pos[0], gcs_pos[1], gcs_pos[2])
            node = Node(
                node_id=node_id,
                node_type=NodeType.GCS,
                position=pos,
                transmission_range=self.scenario.transmission_range
            )
            self.network.add_node(node)
            node_id += 1

        # UGV 생성
        for _ in range(self.scenario.num_ugv):
            pos = Position(
                random.uniform(0, self.scenario.area_width),
                random.uniform(0, self.scenario.area_height),
                0.0
            )
            node = Node(
                node_id=node_id,
                node_type=NodeType.UGV,
                position=pos,
                transmission_range=self.scenario.transmission_range
            )
            self.network.add_node(node)
            node_id += 1

        # UAV 생성
        for _ in range(self.scenario.num_uav):
            pos = Position(
                random.uniform(0, self.scenario.area_width),
                random.uniform(0, self.scenario.area_height),
                random.uniform(50, self.scenario.area_depth)
            )
            node = Node(
                node_id=node_id,
                node_type=NodeType.UAV,
                position=pos,
                transmission_range=self.scenario.transmission_range
            )
            self.network.add_node(node)
            node_id += 1

    def _setup_mobility(self) -> None:
        """이동성 모델 설정."""
        if self.scenario.mobility_model == "random_waypoint":
            self.mobility_model = RandomWaypointModel(
                self.scenario.area_width,
                self.scenario.area_height,
                self.scenario.min_speed,
                self.scenario.max_speed
            )
        elif self.scenario.mobility_model == "gauss_markov":
            self.mobility_model = GaussMarkovModel(
                self.scenario.area_width,
                self.scenario.area_height,
                self.scenario.area_depth
            )

    def _setup_protocols(self) -> None:
        """라우팅 프로토콜 설정."""
        protocol_class = self.PROTOCOL_MAP.get(self.scenario.protocol.lower())
        if not protocol_class:
            raise ValueError(f"Unknown protocol: {self.scenario.protocol}")

        for node in self.network.nodes.values():
            protocol = protocol_class(node)
            protocol.initialize()
            node.routing_protocol = protocol

        # GPSR: Initialize shared location service with all node positions (O(n))
        if self._location_service is not None:
            for node in self.network.nodes.values():
                self._location_service.update_position(node.node_id, node.position)

    def _setup_traffic(self) -> None:
        """트래픽 생성기 설정."""
        for src, dst in self.scenario.traffic_pairs:
            if src in self.network.nodes and dst in self.network.nodes:
                self.traffic_generators.append(TrafficGenerator(
                    source_id=src,
                    dest_id=dst,
                    packet_rate=self.scenario.packet_rate,
                    packet_size=self.scenario.packet_size
                ))

    def run(self) -> MetricsCollector:
        """시뮬레이션 실행."""
        print(f"Starting simulation: {self.scenario.name}")
        print(f"  Protocol: {self.scenario.protocol.upper()}")
        print(f"  Duration: {self.scenario.duration}s")
        print(f"  Nodes: {self.scenario.num_gcs} GCS + {self.scenario.num_ugv} UGV + {self.scenario.num_uav} UAV")
        print(f"  Traffic: {len(self.scenario.traffic_pairs)} pairs ({self.scenario.traffic_mode} mode)")

        while self.current_time < self.scenario.duration:
            self._step()
            self.current_time += self.scenario.time_step

        self._finalize_metrics()
        return self.metrics

    def _step(self) -> None:
        """시뮬레이션 단일 스텝."""
        # 1. 노드 이동 (GCS는 고정)
        if self.mobility_model:
            for node in self.network.nodes.values():
                if node.node_type != NodeType.GCS:
                    self.mobility_model.update_position(node, self.scenario.time_step)

        # 2. 토폴로지 갱신
        self.network.update_topology()

        # 3. 이전 스텝에서 대기 중인 제어 패킷 처리 (RREQ/RREP 전파)
        self._process_control_packets()

        # 4. 프로토콜 업데이트 (새 제어 메시지 생성)
        for node in self.network.nodes.values():
            if node.routing_protocol:
                control_packets = node.routing_protocol.update(self.current_time)
                for pkt in control_packets:
                    self._broadcast_packet(node, pkt)

                # AODV 유니캐스트 패킷 처리 (RREP)
                if hasattr(node.routing_protocol, 'get_pending_unicasts'):
                    unicasts = node.routing_protocol.get_pending_unicasts()
                    for next_hop_id, pkt in unicasts:
                        self._unicast_packet(node, next_hop_id, pkt)

        # 5. 트래픽 생성
        self._generate_traffic()

        # 6. 데이터 패킷 전송
        self._process_packets()

        # 7. 유휴 에너지 소비 (모든 활성 노드)
        for node in self.network.nodes.values():
            if node.is_active:
                node.consume_idle_energy(self.scenario.time_step)

        # GPSR: 위치 업데이트
        self._update_location_service()

    def _process_control_packets(self) -> None:
        """대기 중인 제어 패킷 처리 (한 홉씩 전파)."""
        # 현재 대기 중인 패킷만 처리 (새로 추가되는 것은 다음 스텝에서)
        current_packets = self.pending_control_packets
        self.pending_control_packets = []

        for sender, packet in current_packets:
            self._broadcast_packet(sender, packet)

    def _generate_traffic(self) -> None:
        """데이터 패킷 생성."""
        for gen in self.traffic_generators:
            interval = 1.0 / gen.packet_rate
            while self.current_time - gen.last_send_time >= interval:
                self.packet_id_counter += 1
                gen.packet_counter += 1

                packet = Packet(
                    packet_id=self.packet_id_counter,
                    packet_type=PacketType.DATA,
                    source_id=gen.source_id,
                    destination_id=gen.dest_id,
                    payload=b'x' * gen.packet_size,
                    path=[gen.source_id],
                    created_at=self.current_time
                )

                # GPSR: 목적지 위치 설정
                if self.scenario.protocol.lower() == "gpsr":
                    dest_node = self.network.get_node(gen.dest_id)
                    if dest_node:
                        packet.destination_position = (
                            dest_node.position.x,
                            dest_node.position.y,
                            dest_node.position.z
                        )

                self.pending_packets.append(packet)
                self.metrics.record_packet_sent(packet)
                gen.last_send_time += interval

    def _process_packets(self) -> None:
        """대기 중인 패킷 처리."""
        next_pending = []

        for packet in self.pending_packets:
            current_node_id = packet.path[-1] if packet.path else packet.source_id
            current_node = self.network.get_node(current_node_id)

            if not current_node or not current_node.routing_protocol:
                self.metrics.record_packet_dropped(packet)
                continue

            # 목적지 도착 체크 (먼저 확인)
            if packet.destination_id == current_node_id:
                self.metrics.record_packet_delivered(packet, self.current_time)
                continue

            # AODV: 경로가 없으면 탐색 시작
            if (self.scenario.protocol.lower() == "aodv" and
                packet.packet_type == PacketType.DATA):
                aodv = current_node.routing_protocol
                if aodv.get_next_hop(packet.destination_id) is None:
                    # 경로 탐색 시작 시간 기록
                    if packet.route_discovery_started is None:
                        packet.route_discovery_started = self.current_time
                    rreq = aodv.discover_route(packet.destination_id)
                    if rreq:  # 새로운 탐색인 경우만 브로드캐스트
                        self._broadcast_packet(current_node, rreq)
                    next_pending.append(packet)
                    continue

            # 다음 홉 결정
            next_hop_id = current_node.routing_protocol.get_next_hop(packet.destination_id)

            if next_hop_id is not None and next_hop_id in current_node.neighbors:
                next_node = self.network.get_node(next_hop_id)

                # 송신 에너지 소비
                if not current_node.send_packet(packet):
                    self.metrics.record_packet_dropped(packet)
                    current_node.packets_dropped += 1
                    continue

                # 수신 에너지 소비
                if next_node and not next_node.receive_packet(packet):
                    self.metrics.record_packet_dropped(packet)
                    continue

                # 첫 홉 전송 시간 기록 (경로 확보 후 첫 전송)
                if packet.first_hop_time is None:
                    packet.first_hop_time = self.current_time

                # 포워딩
                packet.hop_count += 1
                packet.path.append(next_hop_id)
                current_node.packets_forwarded += 1
                next_pending.append(packet)
            else:
                # 드랍
                self.metrics.record_packet_dropped(packet)
                current_node.packets_dropped += 1

        self.pending_packets = next_pending

    def _broadcast_packet(self, sender: Node, packet: Packet) -> None:
        """브로드캐스트 패킷 전송. 응답 패킷은 다음 스텝에서 처리."""

        # 송신 에너지 소비 (한 번 전송으로 모든 이웃에게 도달)
        if not sender.send_packet(packet):
            return  # 에너지 부족

        for neighbor_id in sender.neighbors:
            neighbor = self.network.get_node(neighbor_id)
            if neighbor and neighbor.routing_protocol:
                # 수신 에너지 소비
                if not neighbor.receive_packet(packet):
                    continue  # 수신 노드 에너지 부족

                pkt_copy = packet.copy()
                response = neighbor.routing_protocol.handle_packet(pkt_copy)

                # 응답 패킷이 있으면 다음 스텝에서 처리하도록 큐에 추가
                if response is not None:
                    self.pending_control_packets.append((neighbor, response))

    def _unicast_packet(self, sender: Node, next_hop_id: int, packet: Packet) -> None:
        """유니캐스트 패킷 전송 (특정 다음 홉으로)."""

        if next_hop_id not in sender.neighbors:
            return  # 다음 홉이 이웃이 아니면 전송 실패

        neighbor = self.network.get_node(next_hop_id)
        if neighbor and neighbor.routing_protocol:
            # 송신 에너지 소비
            if not sender.send_packet(packet):
                return  # 에너지 부족

            # 수신 에너지 소비
            if not neighbor.receive_packet(packet):
                return  # 수신 노드 에너지 부족

            pkt_copy = packet.copy()
            response = neighbor.routing_protocol.handle_packet(pkt_copy)

            # 응답이 있으면 큐에 추가 (RREP 체인 등)
            if response is not None:
                self.pending_control_packets.append((neighbor, response))

    def _update_location_service(self) -> None:
        """GPSR 위치 서비스 갱신.

        Optimized: O(n) instead of O(n^2) by using shared location service.
        Updates each node's position once in the shared service, rather than
        having each node update its copy of every other node's position.
        """
        if self._location_service is None:
            return

        # O(n) - update each node's position once in the shared service
        for node in self.network.nodes.values():
            self._location_service.update_position(node.node_id, node.position)

    def _finalize_metrics(self) -> None:
        """최종 메트릭 계산."""
        # 시뮬레이션 시간 기록
        self.metrics.simulation_duration = self.current_time

        # 대기 중인 패킷은 드랍으로 처리
        for packet in self.pending_packets:
            self.metrics.record_packet_dropped(packet)

        # 프로토콜 오버헤드 수집
        total_control = 0
        for node in self.network.nodes.values():
            if node.routing_protocol:
                total_control += node.routing_protocol.get_routing_overhead()
        self.metrics.routing_overhead = total_control

        # 네트워크 상태
        self.metrics.final_connectivity = self.network.is_connected()

        # 에너지 통계 수집
        for node in self.network.nodes.values():
            self.metrics.record_node_energy(
                node.node_id,
                node.node_type.value,
                node.get_energy_stats()
            )
        self.metrics.finalize_energy_stats()
