"""성능 지표 수집 모듈."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import statistics

from ..core.packet import Packet


@dataclass
class PacketRecord:
    """패킷 기록."""
    packet_id: int
    source_id: int
    destination_id: int
    send_time: float
    receive_time: float = 0.0
    hop_count: int = 0
    delivered: bool = False
    route_discovery_delay: float = 0.0  # 경로 탐색 대기 시간
    transmission_delay: float = 0.0      # 실제 전송 시간


@dataclass
class NodeEnergyStats:
    """노드별 에너지 통계."""
    node_id: int
    node_type: str
    initial_energy: float
    final_energy: float
    total_consumed: float
    tx_energy: float
    rx_energy: float
    idle_energy: float
    packets_tx: int
    packets_rx: int
    bytes_tx: int
    bytes_rx: int


class MetricsCollector:
    """시뮬레이션 메트릭 수집기."""

    # Maximum number of packet records to keep in memory
    # Older records are discarded to prevent unbounded memory growth
    MAX_PACKET_HISTORY = 10000

    def __init__(self, max_packet_history: int = MAX_PACKET_HISTORY):
        self.packets: Dict[int, PacketRecord] = {}
        self._max_packet_history = max_packet_history
        self._oldest_packet_id: int = 0  # Track for efficient cleanup

        # 카운터
        self.packets_sent: int = 0
        self.packets_delivered: int = 0
        self.packets_dropped: int = 0

        # 지연 시간
        self.delays: List[float] = []
        self.route_discovery_delays: List[float] = []  # 경로 탐색 지연
        self.transmission_delays: List[float] = []     # 전송 지연

        # 프로토콜 오버헤드
        self.routing_overhead: int = 0

        # 네트워크 상태
        self.final_connectivity: bool = True

        # 시뮬레이션 시간
        self.simulation_duration: float = 0.0

        # 에너지 통계
        self.node_energy_stats: Dict[int, NodeEnergyStats] = {}
        self.total_energy_consumed: float = 0.0
        self.total_tx_energy: float = 0.0
        self.total_rx_energy: float = 0.0
        self.total_idle_energy: float = 0.0
        self.nodes_depleted: int = 0  # 에너지 고갈 노드 수

    def record_packet_sent(self, packet: Packet) -> None:
        """패킷 전송 기록."""
        self.packets[packet.packet_id] = PacketRecord(
            packet_id=packet.packet_id,
            source_id=packet.source_id,
            destination_id=packet.destination_id,
            send_time=packet.created_at
        )
        self.packets_sent += 1

        # Limit packet history to prevent unbounded memory growth
        self._cleanup_old_packets()

    def record_packet_delivered(self, packet: Packet, receive_time: float) -> None:
        """패킷 수신 기록."""
        if packet.packet_id in self.packets:
            record = self.packets[packet.packet_id]
            record.receive_time = receive_time
            record.hop_count = packet.hop_count
            record.delivered = True

            # 총 지연
            delay = receive_time - record.send_time
            self.delays.append(delay)

            # 경로 탐색 지연 vs 전송 지연 분리
            if packet.first_hop_time is not None:
                route_delay = packet.first_hop_time - packet.created_at
                trans_delay = receive_time - packet.first_hop_time
                record.route_discovery_delay = route_delay
                record.transmission_delay = trans_delay
                self.route_discovery_delays.append(route_delay)
                self.transmission_delays.append(trans_delay)
            else:
                # 경로 탐색 없이 바로 전송된 경우
                record.route_discovery_delay = 0.0
                record.transmission_delay = delay
                self.route_discovery_delays.append(0.0)
                self.transmission_delays.append(delay)

        self.packets_delivered += 1

    def record_packet_dropped(self, packet: Packet) -> None:
        """패킷 드랍 기록."""
        self.packets_dropped += 1
        # Remove from history since it won't be delivered
        self.packets.pop(packet.packet_id, None)

    def _cleanup_old_packets(self) -> None:
        """Remove old packet records to limit memory usage.

        Uses a simple strategy: when history exceeds max, remove the oldest
        undelivered packets. Delivered packets are kept for statistics.
        """
        if len(self.packets) <= self._max_packet_history:
            return

        # Find and remove oldest undelivered packets
        to_remove = []
        for packet_id, record in self.packets.items():
            if not record.delivered:
                to_remove.append(packet_id)
            if len(self.packets) - len(to_remove) <= self._max_packet_history:
                break

        for packet_id in to_remove:
            del self.packets[packet_id]

    def record_node_energy(self, node_id: int, node_type: str, energy_stats: dict) -> None:
        """노드 에너지 통계 기록."""
        initial = energy_stats['initial_energy']
        current = energy_stats['current_energy']

        # 무한 에너지 (GCS)는 제외
        if initial == float('inf'):
            return

        self.node_energy_stats[node_id] = NodeEnergyStats(
            node_id=node_id,
            node_type=node_type,
            initial_energy=initial,
            final_energy=current,
            total_consumed=energy_stats['total_consumed'],
            tx_energy=energy_stats['tx_energy'],
            rx_energy=energy_stats['rx_energy'],
            idle_energy=energy_stats['idle_energy'],
            packets_tx=energy_stats['packets_tx'],
            packets_rx=energy_stats['packets_rx'],
            bytes_tx=energy_stats['bytes_tx'],
            bytes_rx=energy_stats['bytes_rx'],
        )

    def finalize_energy_stats(self) -> None:
        """에너지 통계 집계."""
        self.total_energy_consumed = 0.0
        self.total_tx_energy = 0.0
        self.total_rx_energy = 0.0
        self.total_idle_energy = 0.0
        self.nodes_depleted = 0

        for stats in self.node_energy_stats.values():
            self.total_energy_consumed += stats.total_consumed
            self.total_tx_energy += stats.tx_energy
            self.total_rx_energy += stats.rx_energy
            self.total_idle_energy += stats.idle_energy

            if stats.final_energy <= 0:
                self.nodes_depleted += 1

    @property
    def packet_delivery_ratio(self) -> float:
        """Packet Delivery Ratio (PDR)."""
        if self.packets_sent == 0:
            return 0.0
        return self.packets_delivered / self.packets_sent

    @property
    def average_delay(self) -> float:
        """평균 End-to-End 지연 (초)."""
        if not self.delays:
            return 0.0
        return statistics.mean(self.delays)

    @property
    def delay_std(self) -> float:
        """지연 표준편차."""
        if len(self.delays) < 2:
            return 0.0
        return statistics.stdev(self.delays)

    @property
    def average_route_discovery_delay(self) -> float:
        """평균 경로 탐색 지연 (초)."""
        if not self.route_discovery_delays:
            return 0.0
        return statistics.mean(self.route_discovery_delays)

    @property
    def average_transmission_delay(self) -> float:
        """평균 전송 지연 (초)."""
        if not self.transmission_delays:
            return 0.0
        return statistics.mean(self.transmission_delays)

    @property
    def average_hop_count(self) -> float:
        """평균 홉 수."""
        delivered = [r for r in self.packets.values() if r.delivered]
        if not delivered:
            return 0.0
        return statistics.mean(r.hop_count for r in delivered)

    @property
    def throughput(self) -> float:
        """처리량 (패킷/초)."""
        if self.simulation_duration <= 0:
            return 0.0
        return self.packets_delivered / self.simulation_duration

    @property
    def average_energy_consumption(self) -> float:
        """평균 에너지 소비 (Joules/노드)."""
        if not self.node_energy_stats:
            return 0.0
        return self.total_energy_consumed / len(self.node_energy_stats)

    @property
    def energy_efficiency(self) -> float:
        """에너지 효율 (전달된 비트 / Joule)."""
        if self.total_energy_consumed <= 0:
            return 0.0
        # 전달된 총 바이트 계산
        delivered_bytes = sum(
            s.bytes_tx for s in self.node_energy_stats.values()
        )
        return (delivered_bytes * 8) / self.total_energy_consumed

    @property
    def average_remaining_energy(self) -> float:
        """평균 잔여 에너지 비율 (%)."""
        if not self.node_energy_stats:
            return 100.0
        ratios = []
        for stats in self.node_energy_stats.values():
            if stats.initial_energy > 0:
                ratios.append(stats.final_energy / stats.initial_energy * 100)
        return statistics.mean(ratios) if ratios else 100.0

    def get_summary(self) -> Dict:
        """메트릭 요약."""
        return {
            "packets_sent": self.packets_sent,
            "packets_delivered": self.packets_delivered,
            "packets_dropped": self.packets_dropped,
            "pdr": f"{self.packet_delivery_ratio:.2%}",
            "avg_delay_ms": f"{self.average_delay * 1000:.2f}",
            "route_discovery_delay_ms": f"{self.average_route_discovery_delay * 1000:.2f}",
            "transmission_delay_ms": f"{self.average_transmission_delay * 1000:.2f}",
            "delay_std_ms": f"{self.delay_std * 1000:.2f}",
            "avg_hop_count": f"{self.average_hop_count:.2f}",
            "routing_overhead": self.routing_overhead,
            "throughput": f"{self.throughput:.2f}",
            "network_connected": self.final_connectivity,
            # 에너지 메트릭
            "total_energy_j": f"{self.total_energy_consumed:.2f}",
            "tx_energy_j": f"{self.total_tx_energy:.2f}",
            "rx_energy_j": f"{self.total_rx_energy:.2f}",
            "idle_energy_j": f"{self.total_idle_energy:.2f}",
            "avg_energy_per_node_j": f"{self.average_energy_consumption:.2f}",
            "avg_remaining_energy_pct": f"{self.average_remaining_energy:.1f}",
            "energy_efficiency_bpj": f"{self.energy_efficiency:.0f}",
            "nodes_depleted": self.nodes_depleted,
        }

    def print_summary(self) -> None:
        """메트릭 출력."""
        summary = self.get_summary()
        print("\n" + "=" * 50)
        print("Simulation Results")
        print("=" * 50)
        print(f"  Packets Sent:      {summary['packets_sent']}")
        print(f"  Packets Delivered: {summary['packets_delivered']}")
        print(f"  Packets Dropped:   {summary['packets_dropped']}")
        print(f"  PDR:               {summary['pdr']}")
        print(f"  Avg Delay:         {summary['avg_delay_ms']} ms")
        print(f"    - Route Discovery: {summary['route_discovery_delay_ms']} ms")
        print(f"    - Transmission:    {summary['transmission_delay_ms']} ms")
        print(f"  Delay Std:         {summary['delay_std_ms']} ms")
        print(f"  Avg Hop Count:     {summary['avg_hop_count']}")
        print(f"  Routing Overhead:  {summary['routing_overhead']} packets")
        print(f"  Throughput:        {summary['throughput']} pkt/s")
        print(f"  Network Connected: {summary['network_connected']}")
        print("-" * 50)
        print("  Energy Metrics:")
        print(f"    Total Energy:    {summary['total_energy_j']} J")
        print(f"    TX Energy:       {summary['tx_energy_j']} J")
        print(f"    RX Energy:       {summary['rx_energy_j']} J")
        print(f"    Idle Energy:     {summary['idle_energy_j']} J")
        print(f"    Avg per Node:    {summary['avg_energy_per_node_j']} J")
        print(f"    Avg Remaining:   {summary['avg_remaining_energy_pct']}%")
        print(f"    Efficiency:      {summary['energy_efficiency_bpj']} bits/J")
        print(f"    Nodes Depleted:  {summary['nodes_depleted']}")
        print("=" * 50)
