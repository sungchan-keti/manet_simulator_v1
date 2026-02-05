"""토폴로지 시각화와 함께 시뮬레이션 실행."""
import sys
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.simulation.scenario import Scenario
from src.simulation.engine import SimulationEngine
from src.visualization.topology import TopologyVisualizer


def run_with_visualization(
    protocol: str = "olsr",
    duration: float = 30.0,
    capture_interval: float = 5.0,
    show_range: bool = False,
    mode_3d: bool = True
):
    """시각화와 함께 시뮬레이션 실행.

    Args:
        protocol: 프로토콜 이름 (olsr, aodv, gpsr)
        duration: 시뮬레이션 시간 (초)
        capture_interval: 토폴로지 캡처 간격 (초)
        show_range: 전송 범위 표시 여부
        mode_3d: 3D 시각화 사용 여부
    """
    print(f"\n{'='*60}")
    print(f"{'3D ' if mode_3d else ''}토폴로지 시각화 시뮬레이션 - {protocol.upper()}")
    print(f"{'='*60}")

    # 시나리오 설정
    scenario = Scenario(
        name=f"visualization_{protocol}",
        duration=duration,
        area_width=500.0,
        area_height=500.0,
        area_depth=100.0,
        num_gcs=1,
        num_ugv=10,
        num_uav=5,
        transmission_range=180.0,
        traffic_mode="gcs",
        packet_rate=2.0,
        min_speed=1.0,
        max_speed=5.0,
        protocol=protocol
    )

    # 시뮬레이션 엔진 생성
    engine = SimulationEngine(scenario)

    # 시각화 도구 생성
    output_dir = f"results/topology/{protocol}"
    visualizer = TopologyVisualizer(output_dir=output_dir)

    print(f"시뮬레이션 시간: {duration}초")
    print(f"캡처 간격: {capture_interval}초")
    print(f"시각화 모드: {'3D' if mode_3d else '2D'}")
    print(f"출력 디렉토리: {output_dir}")
    print()

    # 캡처 함수 선택
    if mode_3d:
        def capture(time, suffix=""):
            return visualizer.capture_topology_3d(
                engine.network,
                time,
                protocol.upper(),
                show_links=True,
                show_ground=True,
                title_suffix=suffix
            )
    else:
        def capture(time, suffix=""):
            return visualizer.capture_topology(
                engine.network,
                time,
                protocol.upper(),
                show_links=True,
                show_range=show_range,
                title_suffix=suffix
            )

    # 초기 상태 캡처
    saved_files = []
    filepath = capture(0.0, "[Initial]")
    saved_files.append(filepath)
    print(f"[t=0.0s] 토폴로지 저장: {filepath}")

    # 시뮬레이션 실행 (캡처 간격마다 저장)
    next_capture_time = capture_interval

    while engine.current_time < scenario.duration:
        # 한 스텝 실행
        engine._step()
        engine.current_time += scenario.time_step

        # 캡처 시간 도달 시 토폴로지 저장
        if engine.current_time >= next_capture_time:
            filepath = capture(engine.current_time)
            saved_files.append(filepath)
            print(f"[t={engine.current_time:.1f}s] 토폴로지 저장: {filepath}")
            next_capture_time += capture_interval

    # 최종 상태 캡처
    filepath = capture(engine.current_time, "[Final]")
    saved_files.append(filepath)
    print(f"[t={engine.current_time:.1f}s] 토폴로지 저장: {filepath}")

    # 메트릭 마무리
    engine._finalize_metrics()

    print(f"\n총 {len(saved_files)}개의 {'3D ' if mode_3d else ''}토폴로지 이미지 저장 완료")
    print(f"저장 위치: {output_dir}/")

    return saved_files


def run_all_protocols(mode_3d: bool = True):
    """3개 프로토콜 모두 시각화."""
    protocols = ["olsr", "aodv", "gpsr"]
    all_files = {}

    for protocol in protocols:
        files = run_with_visualization(
            protocol=protocol,
            duration=30.0,
            capture_interval=5.0,
            show_range=False,
            mode_3d=mode_3d
        )
        all_files[protocol] = files
        print()

    print("\n" + "="*60)
    print(f"모든 프로토콜 {'3D ' if mode_3d else ''}시각화 완료")
    print("="*60)
    for protocol, files in all_files.items():
        print(f"  {protocol.upper()}: {len(files)}개 이미지")

    return all_files


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='MANET 토폴로지 시각화')
    parser.add_argument('-p', '--protocol', type=str, default='all',
                        choices=['olsr', 'aodv', 'gpsr', 'all'],
                        help='프로토콜 선택 (기본: all)')
    parser.add_argument('-d', '--duration', type=float, default=30.0,
                        help='시뮬레이션 시간 (초)')
    parser.add_argument('-i', '--interval', type=float, default=5.0,
                        help='캡처 간격 (초)')
    parser.add_argument('--show-range', action='store_true',
                        help='전송 범위 표시 (2D 모드)')
    parser.add_argument('--2d', dest='mode_2d', action='store_true',
                        help='2D 시각화 사용 (기본: 3D)')

    args = parser.parse_args()
    mode_3d = not args.mode_2d

    if args.protocol == 'all':
        run_all_protocols(mode_3d=mode_3d)
    else:
        run_with_visualization(
            protocol=args.protocol,
            duration=args.duration,
            capture_interval=args.interval,
            show_range=args.show_range,
            mode_3d=mode_3d
        )
