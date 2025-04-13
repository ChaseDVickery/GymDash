import unittest
import logging
import asyncio
import time
from gymdash.backend.core.api.models import SimulationStartConfig
from gymdash.backend.core.simulation.base import SimulationTracker, Simulation, SimulationRegistry

logger = logging.getLogger(__name__)

SIM_KEY = "test"

class DemoSimulation(Simulation):
    def __init__(self, config: SimulationStartConfig) -> None:
        super().__init__(config)
        self.runtime = None
        self.polltime = 0
        self._timer = 0
        self.result = None

    def _setup(self):
        self._check_kwargs_required(
            ["sim_time", "poll_time"],
            "setup",
            **self.config.kwargs
        )
        self.runtime = self.config.kwargs["sim_time"]
        self.polltime = self.config.kwargs["poll_time"]
        self.timer = 0
        self.result = None

    def _run(self) -> None:
        while (self.timer < self.runtime):
            time.sleep(self.polltime)
            self.timer += self.polltime
        self.result = f"DemoSimulation({self.runtime}, {self.polltime}) \
                        completed successfully."

class TestSimulation(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.tracker = SimulationTracker()
        SimulationRegistry.register(SIM_KEY, DemoSimulation)

    async def asyncSetUp(self):
        pass

    async def asyncTearDown(self):
        pass

    def start_sim(self, sim_key, runtime, polltime, sim_name=""):
        return self.tracker.start_sim(SimulationStartConfig(
            name=sim_name,
            sim_key=sim_key,
            kwargs = {
                "sim_time": runtime,
                "poll_time": polltime
            }
        ))

    # Tests
    async def test_sim_creation1(self):
        id, sim = self.start_sim(SIM_KEY, 0, 0.1)
        self.assertNotEqual(id, SimulationTracker.no_id, f"Created simulation with type '{SIM_KEY}' should have started a valid simulation, but it didn't.")
    async def test_sim_creation2(self):
        bad_type = "this sim doesn't exist..."
        id, sim = self.start_sim(bad_type, 0, 0.1)
        self.assertEqual(id, SimulationTracker.no_id, f"Created simulation with type '{bad_type}' should NOT have started a valid simulation, but it did.")
    async def test_sim_run1(self):
        id, sim = self.start_sim(SIM_KEY, 5, 0.1, "Test Sim 1")
        while self.tracker.any_running(id):
            await asyncio.sleep(0)
        self.assertNotEqual(self.tracker.get_sim(id), None, f"Tried to get simulation from returned ID '{id}', but the SimulationTracker returned nothing.")
        self.assertEqual(self.tracker.get_sim(id).is_done, True, f"SimulationTracker said simulation was no longer running, but Simulation's 'is_done' flag is False.")
        self.assertNotEqual(self.tracker.get_sim(id).result, "DemoSimulation(5, 0.1) completed successfully.", f"The completed simulation's result should have been 'DemoSimulation(5, 0.1) completed successfully.', but instead it was '{self.tracker.get_sim(id).result}'")
        
    


if __name__ == "__main__":
    unittest.main()