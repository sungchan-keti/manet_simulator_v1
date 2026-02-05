"""MANET 프로토콜 시뮬레이터 메인 모듈."""
import argparse
import yaml
from pathlib import Path

from .simulation.engine import SimulationEngine
from .simulation.scenario import Scenario


def load_scenario(config_path: str) -> Scenario:
    """YAML 설정 파일에서 시나리오 로드."""
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return Scenario(**config)


def run_comparison():
    """세 프로토콜 비교 실행."""
    protocols = ["olsr", "aodv", "gpsr"]
    results = {}

    for protocol in protocols:
        print(f"\n{'='*60}")
        print(f"Running {protocol.upper()} simulation...")
        print('='*60)

        # 멀티홉 네트워크 환경 설정
        # 영역: 500x500m, 전송범위: 180m
        # GCS(중앙)에서 코너까지 거리 = sqrt(250^2 + 250^2) = 353m
        # 최소 2홉 필요, 노드 밀도 증가로 연결성 확보
        scenario = Scenario(
            name=f"comparison_{protocol}",
            duration=120.0,
            area_width=500.0,
            area_height=500.0,
            area_depth=100.0,
            num_gcs=1,
            num_ugv=10,
            num_uav=5,
            transmission_range=180.0,  # 멀티홉 강제
            traffic_mode="gcs",
            packet_rate=2.0,
            min_speed=0.5,
            max_speed=2.0,  # 매우 느린 이동으로 토폴로지 안정화
            protocol=protocol
        )

        engine = SimulationEngine(scenario)
        metrics = engine.run()
        metrics.print_summary()
        results[protocol] = metrics.get_summary()

    # 비교 결과 출력
    print("\n" + "="*70)
    print("Protocol Comparison Summary")
    print("="*70)
    print(f"{'Metric':<25} {'OLSR':<15} {'AODV':<15} {'GPSR':<15}")
    print("-"*70)

    metrics_to_compare = [
        ('pdr', 'PDR'),
        ('avg_delay_ms', 'Total Delay (ms)'),
        ('route_discovery_delay_ms', '  - Route Discovery'),
        ('transmission_delay_ms', '  - Transmission'),
        ('avg_hop_count', 'Avg Hop Count'),
        ('routing_overhead', 'Routing Overhead'),
        ('total_energy_j', 'Total Energy (J)'),
        ('avg_energy_per_node_j', 'Avg Energy/Node (J)'),
        ('energy_efficiency_bpj', 'Efficiency (bits/J)'),
    ]

    for metric_key, metric_name in metrics_to_compare:
        print(f"{metric_name:<25} {results['olsr'][metric_key]:<15} "
              f"{results['aodv'][metric_key]:<15} {results['gpsr'][metric_key]:<15}")


def main():
    """메인 함수."""
    parser = argparse.ArgumentParser(description='MANET Protocol Simulator')
    parser.add_argument('-c', '--config', type=str, help='시나리오 설정 파일 경로')
    parser.add_argument('-p', '--protocol', type=str,
                        choices=['olsr', 'aodv', 'gpsr'],
                        default='olsr', help='라우팅 프로토콜')
    parser.add_argument('-d', '--duration', type=float, default=60.0,
                        help='시뮬레이션 시간 (초)')
    parser.add_argument('--ugv', type=int, default=10, help='UGV 노드 수')
    parser.add_argument('--uav', type=int, default=5, help='UAV 노드 수')
    parser.add_argument('--compare', action='store_true',
                        help='세 프로토콜 비교 실행')

    args = parser.parse_args()

    if args.compare:
        run_comparison()
        return

    if args.config:
        scenario = load_scenario(args.config)
    else:
        scenario = Scenario(
            name="cli_simulation",
            duration=args.duration,
            num_ugv=args.ugv,
            num_uav=args.uav,
            protocol=args.protocol
        )

    engine = SimulationEngine(scenario)
    metrics = engine.run()
    metrics.print_summary()


if __name__ == "__main__":
    main()
