# must use with full install

import asyncio
import argparse
import logging

from gymdash.backend.project import ProjectManager
from gymdash.start import add_gymdash_arguments
from gymdash.backend.core.api.models import SimulationStartConfig
from gymdash.backend.core.simulation.manage import SimulationRegistry, SimulationTracker
from gymdash.backend.core.simulation.examples import StableBaselinesSimulation

logger = logging.getLogger(__name__)

async def setup_project_manager(args):
    ProjectManager.setup_from_args(args)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser = add_gymdash_arguments(parser)
    args = parser.parse_args()
    print(args)

    asyncio.run(setup_project_manager(args))

    tracker = SimulationTracker()
    
    SimulationRegistry.register(
        "demo",
        StableBaselinesSimulation,
        SimulationStartConfig(
            name="test",
            sim_key="Acrobot-v1",
            kwargs = {
                "num_steps": 5000,
                "env": "Acrobot-v1",
                "episode_trigger": lambda x: x%2==0
            }
        )
    )

    # Custom
    custom_sim2 = SimulationRegistry.make("demo")
    tracker.start_sim(custom_sim2)
