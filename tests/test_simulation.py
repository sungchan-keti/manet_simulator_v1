"""시뮬레이션 테스트."""
import pytest

from src.simulation.scenario import Scenario
from src.simulation.engine import SimulationEngine


class TestScenario:
    def test_default_scenario(self):
        scenario = Scenario()
        assert scenario.duration == 100.0
        assert scenario.num_ugv == 10
        assert scenario.num_uav == 5
        assert scenario.protocol == "olsr"

    def test_custom_scenario(self):
        scenario = Scenario(
            name="test",
            duration=50.0,
            num_ugv=5,
            num_uav=3,
            protocol="aodv"
        )
        assert scenario.name == "test"
        assert scenario.duration == 50.0
        assert scenario.protocol == "aodv"


class TestSimulationEngine:
    def test_engine_creation(self):
        scenario = Scenario(
            duration=10.0,
            num_ugv=3,
            num_uav=2,
            protocol="olsr"
        )
        engine = SimulationEngine(scenario)

        # 1 GCS + 3 UGV + 2 UAV = 6 nodes
        assert len(engine.network.nodes) == 6
        assert engine.current_time == 0.0

    def test_short_simulation(self):
        scenario = Scenario(
            duration=5.0,
            time_step=0.5,
            num_ugv=4,
            num_uav=2,
            packet_rate=2.0,
            protocol="olsr"
        )
        engine = SimulationEngine(scenario)
        metrics = engine.run()

        assert metrics.packets_sent > 0
        assert engine.current_time >= scenario.duration

    @pytest.mark.parametrize("protocol", ["olsr", "aodv", "gpsr"])
    def test_all_protocols(self, protocol):
        scenario = Scenario(
            duration=3.0,
            num_ugv=4,
            num_uav=2,
            protocol=protocol
        )
        engine = SimulationEngine(scenario)
        metrics = engine.run()

        # 시뮬레이션이 정상 완료되어야 함
        assert engine.current_time >= scenario.duration
