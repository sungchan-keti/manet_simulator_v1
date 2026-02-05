"""에너지 소모 모델."""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class RadioState(Enum):
    """무선 상태."""
    SLEEP = "sleep"
    IDLE = "idle"
    RECEIVE = "receive"
    TRANSMIT = "transmit"


@dataclass
class EnergyModel:
    """무선 네트워크 에너지 소모 모델.

    IEEE 802.11 기반 에너지 파라미터 사용.
    참고: Feeney & Nilsson, "Investigating the Energy Consumption of a Wireless Network Interface"
    """

    # 전력 소모 (Watts)
    tx_power: float = 1.4      # 송신 전력 (W)
    rx_power: float = 1.0      # 수신 전력 (W)
    idle_power: float = 0.8    # 유휴 전력 (W)
    sleep_power: float = 0.05  # 슬립 전력 (W)

    # 전송 파라미터
    data_rate: float = 2e6     # 데이터 전송률 (bps) - 2 Mbps

    # 거리 기반 증폭 에너지 (선택적)
    # E_amp = amplifier_energy * distance^path_loss_exp
    amplifier_energy: float = 100e-12  # pJ/bit/m^2
    path_loss_exp: float = 2.0         # 경로 손실 지수

    # 초기 에너지 (Joules)
    initial_energy: float = 10000.0    # 10000 J (약 2.8 Wh)

    def calculate_tx_energy(self, packet_size_bytes: int, distance: float = 0) -> float:
        """송신 에너지 계산 (Joules).

        E_tx = P_tx * (packet_size / data_rate) + E_amp * packet_size * distance^n

        Args:
            packet_size_bytes: 패킷 크기 (bytes)
            distance: 전송 거리 (meters), 0이면 거리 독립적

        Returns:
            송신에 필요한 에너지 (Joules)
        """
        packet_size_bits = packet_size_bytes * 8
        tx_time = packet_size_bits / self.data_rate

        # 기본 송신 에너지
        energy = self.tx_power * tx_time

        # 거리 기반 증폭 에너지 (선택적)
        if distance > 0:
            energy += self.amplifier_energy * packet_size_bits * (distance ** self.path_loss_exp)

        return energy

    def calculate_rx_energy(self, packet_size_bytes: int) -> float:
        """수신 에너지 계산 (Joules).

        E_rx = P_rx * (packet_size / data_rate)

        Args:
            packet_size_bytes: 패킷 크기 (bytes)

        Returns:
            수신에 필요한 에너지 (Joules)
        """
        packet_size_bits = packet_size_bytes * 8
        rx_time = packet_size_bits / self.data_rate
        return self.rx_power * rx_time

    def calculate_idle_energy(self, duration: float) -> float:
        """유휴 상태 에너지 계산 (Joules).

        Args:
            duration: 유휴 시간 (seconds)

        Returns:
            유휴 상태 에너지 (Joules)
        """
        return self.idle_power * duration

    def calculate_sleep_energy(self, duration: float) -> float:
        """슬립 상태 에너지 계산 (Joules).

        Args:
            duration: 슬립 시간 (seconds)

        Returns:
            슬립 상태 에너지 (Joules)
        """
        return self.sleep_power * duration


@dataclass
class NodeEnergy:
    """노드별 에너지 상태 추적."""

    initial_energy: float = 10000.0  # 초기 에너지 (J)
    current_energy: float = 10000.0  # 현재 에너지 (J)

    # 에너지 소모 통계
    tx_energy_consumed: float = 0.0   # 송신에 소모된 에너지
    rx_energy_consumed: float = 0.0   # 수신에 소모된 에너지
    idle_energy_consumed: float = 0.0 # 유휴에 소모된 에너지
    total_energy_consumed: float = 0.0

    # 패킷 통계
    packets_transmitted: int = 0
    packets_received: int = 0
    bytes_transmitted: int = 0
    bytes_received: int = 0

    def consume_tx_energy(self, energy: float, packet_size: int) -> bool:
        """송신 에너지 소모.

        Returns:
            에너지가 충분하면 True, 부족하면 False
        """
        if self.current_energy < energy:
            return False

        self.current_energy -= energy
        self.tx_energy_consumed += energy
        self.total_energy_consumed += energy
        self.packets_transmitted += 1
        self.bytes_transmitted += packet_size
        return True

    def consume_rx_energy(self, energy: float, packet_size: int) -> bool:
        """수신 에너지 소모."""
        if self.current_energy < energy:
            return False

        self.current_energy -= energy
        self.rx_energy_consumed += energy
        self.total_energy_consumed += energy
        self.packets_received += 1
        self.bytes_received += packet_size
        return True

    def consume_idle_energy(self, energy: float) -> bool:
        """유휴 에너지 소모."""
        if self.current_energy < energy:
            return False

        self.current_energy -= energy
        self.idle_energy_consumed += energy
        self.total_energy_consumed += energy
        return True

    @property
    def remaining_ratio(self) -> float:
        """남은 에너지 비율 (0.0 ~ 1.0)."""
        return self.current_energy / self.initial_energy if self.initial_energy > 0 else 0.0

    @property
    def is_alive(self) -> bool:
        """에너지가 남아있는지 여부."""
        return self.current_energy > 0

    def get_energy_per_bit_tx(self) -> float:
        """송신 비트당 에너지 (J/bit)."""
        if self.bytes_transmitted > 0:
            return self.tx_energy_consumed / (self.bytes_transmitted * 8)
        return 0.0

    def get_energy_per_bit_rx(self) -> float:
        """수신 비트당 에너지 (J/bit)."""
        if self.bytes_received > 0:
            return self.rx_energy_consumed / (self.bytes_received * 8)
        return 0.0
