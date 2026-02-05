# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

UGV/UAV MANET (Mobile Ad-hoc Network) 프로토콜 시뮬레이터. OLSR, AODV, GPSR 세 가지 라우팅 프로토콜의 성능을 비교 검증합니다.

## Commands

```bash
# 의존성 설치
pip install -r requirements.txt

# 시뮬레이션 실행
python -m src.main                          # 기본 OLSR 시뮬레이션
python -m src.main -p aodv                  # AODV 프로토콜
python -m src.main -p gpsr                  # GPSR 프로토콜
python -m src.main --compare                # 세 프로토콜 비교
python -m src.main -c configs/default.yaml  # YAML 설정 파일 사용

# 테스트
python -m pytest tests/ -v                  # 전체 테스트
python -m pytest tests/test_protocols.py -v # 특정 테스트 파일
python -m pytest tests/ -k "test_olsr"      # 특정 테스트만
```

## Architecture

```
src/
├── core/           # 핵심 컴포넌트 (Node, Network, Packet, Position)
├── protocols/      # 라우팅 프로토콜 구현
│   ├── base.py     # RoutingProtocol ABC
│   ├── olsr.py     # Proactive: HELLO/TC 메시지, MPR 선택
│   ├── aodv.py     # Reactive: RREQ/RREP/RERR, 온디맨드 경로 탐색
│   └── gpsr.py     # Geographic: Greedy/Perimeter 포워딩
├── mobility/       # 이동성 모델
│   ├── random_waypoint.py     # UGV용 기본 모델
│   ├── gauss_markov.py        # UAV용 부드러운 이동
│   └── reference_point_group.py # 그룹/편대 이동
├── simulation/     # 시뮬레이션 엔진
│   ├── engine.py   # 메인 시뮬레이션 루프
│   └── scenario.py # 시나리오 설정 클래스
└── metrics/        # 성능 지표 수집 (PDR, Delay, Throughput, Overhead)
```

## Key Concepts

- **NodeType**: UGV (z=0 지상), UAV (z>0 공중)
- **PacketType**: DATA, HELLO, TC, RREQ, RREP, RERR, BEACON
- **MobilityModel**: 노드 이동 패턴 (update_position 메서드)
- **RoutingProtocol**: 경로 결정 (get_next_hop, handle_packet 메서드)

## Adding New Protocols

1. `src/protocols/`에 새 파일 생성
2. `RoutingProtocol` 상속, `name`, `initialize`, `update`, `handle_packet`, `get_next_hop` 구현
3. `SimulationEngine.PROTOCOL_MAP`에 등록

## Metrics

- PDR (Packet Delivery Ratio): 전송 성공률
- End-to-End Delay: 패킷 지연 시간
- Routing Overhead: 제어 패킷 수
- Throughput: 처리량 (pkt/s)
