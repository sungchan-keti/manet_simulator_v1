# MANET Protocol Simulator

A multi-hop network (MANET) simulator for UGV (Unmanned Ground Vehicle) and UAV (Unmanned Aerial Vehicle) environments. Compares the performance of three routing protocols: OLSR, AODV, and GPSR.

## Features

- **Three Routing Protocol Implementations**
  - OLSR (Proactive): HELLO/TC messages, MPR selection
  - AODV (Reactive): RREQ/RREP on-demand route discovery
  - GPSR (Geographic): Greedy/Perimeter forwarding

- **Realistic Simulation Environment**
  - 3D space (UGV: ground level, UAV: airborne)
  - Multiple mobility models (Random Waypoint, Gauss-Markov)
  - IEEE 802.11-based energy model

- **Performance Metrics**
  - PDR (Packet Delivery Ratio)
  - End-to-End Delay (route discovery + transmission)
  - Routing Overhead
  - Energy Consumption

- **3D Topology Visualization**

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/ -v
```

## Quick Start

```bash
# Single protocol simulation
python -m src.main -p olsr -d 60

# Compare all three protocols
python -m src.main --compare

# 3D topology visualization
python -m src.run_visualization --protocol all
```

## Usage

### Command-Line Options

```bash
python -m src.main [options]

Options:
  -p, --protocol    Select protocol (olsr, aodv, gpsr)
  -d, --duration    Simulation duration in seconds
  --ugv             Number of UGV nodes
  --uav             Number of UAV nodes
  --compare         Run comparison across all three protocols
  -c, --config      Path to YAML configuration file
```

### Using a Configuration File

```bash
python -m src.main -c configs/default.yaml
```

## Project Structure

```
manet/
├── src/
│   ├── core/                  # Core components
│   │   ├── node.py            # Node types (UGV, UAV, GCS)
│   │   ├── packet.py          # Packet definitions
│   │   ├── network.py         # Network topology
│   │   ├── energy.py          # Energy model
│   │   ├── spatial_index.py   # Spatial indexing (optimization)
│   │   └── location_service.py # Location service
│   ├── protocols/             # Routing protocols
│   │   ├── olsr.py            # OLSR implementation
│   │   ├── aodv.py            # AODV implementation
│   │   └── gpsr.py            # GPSR implementation
│   ├── mobility/              # Mobility models
│   │   ├── random_waypoint.py
│   │   └── gauss_markov.py
│   ├── simulation/            # Simulation engine
│   │   ├── engine.py
│   │   └── scenario.py
│   ├── metrics/               # Performance measurement
│   │   └── collector.py
│   └── visualization/         # Visualization
│       └── topology.py        # 2D/3D topology
├── tests/                     # Unit tests
├── configs/                   # YAML configuration files
└── results/                   # Simulation results
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
