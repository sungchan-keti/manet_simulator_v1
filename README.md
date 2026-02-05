# MANET Protocol Simulator

UGV(무인지상차량) 및 UAV(무인항공기) 멀티홉 네트워크(MANET) 시뮬레이터입니다.
OLSR, AODV, GPSR 세 가지 라우팅 프로토콜의 성능을 비교 분석합니다.

## Features

- **3가지 라우팅 프로토콜 구현**
  - OLSR (Proactive): HELLO/TC 메시지, MPR 선택
  - AODV (Reactive): RREQ/RREP 온디맨드 경로 탐색
  - GPSR (Geographic): Greedy/Perimeter 포워딩

- **현실적인 시뮬레이션 환경**
  - 3D 공간 (UGV: 지상, UAV: 공중)
  - 다양한 이동성 모델 (Random Waypoint, Gauss-Markov)
  - IEEE 802.11 기반 에너지 모델

- **성능 측정 지표**
  - PDR (Packet Delivery Ratio)
  - End-to-End Delay (경로 탐색 + 전송)
  - Routing Overhead
  - Energy Consumption

- **3D 토폴로지 시각화**

## Installation

```bash
# 의존성 설치
pip install -r requirements.txt

# 테스트 실행
python -m pytest tests/ -v
```

## Quick Start

```bash
# 단일 프로토콜 시뮬레이션
python -m src.main -p olsr -d 60

# 3개 프로토콜 비교
python -m src.main --compare

# 3D 토폴로지 시각화
python -m src.run_visualization --protocol all
```

## Usage

### 명령줄 옵션

```bash
python -m src.main [options]

Options:
  -p, --protocol    프로토콜 선택 (olsr, aodv, gpsr)
  -d, --duration    시뮬레이션 시간 (초)
  --ugv             UGV 노드 수
  --uav             UAV 노드 수
  --compare         3개 프로토콜 비교 실행
  -c, --config      YAML 설정 파일 경로
```

### 설정 파일 사용

```bash
python -m src.main -c configs/default.yaml
```

## Project Structure

```
manet/
├── src/
│   ├── core/              # 핵심 컴포넌트
│   │   ├── node.py        # 노드 (UGV, UAV, GCS)
│   │   ├── packet.py      # 패킷 정의
│   │   ├── network.py     # 네트워크 토폴로지
│   │   ├── energy.py      # 에너지 모델
│   │   ├── spatial_index.py   # 공간 인덱싱 (최적화)
│   │   └── location_service.py # 위치 서비스
│   ├── protocols/         # 라우팅 프로토콜
│   │   ├── olsr.py        # OLSR 구현
│   │   ├── aodv.py        # AODV 구현
│   │   └── gpsr.py        # GPSR 구현
│   ├── mobility/          # 이동성 모델
│   │   ├── random_waypoint.py
│   │   └── gauss_markov.py
│   ├── simulation/        # 시뮬레이션 엔진
│   │   ├── engine.py
│   │   └── scenario.py
│   ├── metrics/           # 성능 측정
│   │   └── collector.py
│   └── visualization/     # 시각화
│       └── topology.py    # 2D/3D 토폴로지
├── tests/                 # 단위 테스트
├── configs/               # YAML 설정 파일
└── results/               # 시뮬레이션 결과
```

## Protocol Comparison Results

| Metric | OLSR | AODV | GPSR |
|--------|------|------|------|
| PDR | 91.10% | **100.00%** | 99.41% |
| Delay | **142.96ms** | 738.55ms | 147.45ms |
| Overhead | 15,050 | **624** | 1,824 |
| Energy | 1,481J | **1,461J** | 1,463J |

## Screenshots

### 3D Network Topology
![3D Topology](results/topology/olsr/topology_3d_olsr_0003.png)

## Requirements

- Python 3.9+
- numpy
- matplotlib
- networkx
- pyyaml
- pytest

## License

MIT License

## Author

Created with Claude Code
