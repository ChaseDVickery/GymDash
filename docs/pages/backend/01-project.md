# Projects
## Layout
Because it allows you to create and interact with running simulations, GymDash is
project-based. When started with default arguments, GymDash creates a project
folder at `./.gymdash-projects/`. This project folder is then populated with the
following folders:
- `db/`: Contains the SQLite database storing simulation and project information and
other logs.
- `resources/`: Should contain project-wide resources that can be shared between multiple simulations, e.g. datasets, pretrained models, etc.
- `sims/`: Contains subfolders that each contain Simulation-specific resources and logs, e.g. model checkpoints, tensorboard logs, produced media, etc.

## Database Tables
Work in progress...
<!-- (TODO: Subject to change) -->

### `simulations`
|column|description|
|---|---|
|`sim_id`|**Primary key.** UUID for the Simulation.|
|`name`|Display name.|
|`created`|Datetime when Simulation created.|
|`started`|Datetime when Simulation started.|
|`ended`|Datetime when Simulation ended.|
|`is_done`|Whether the simulation is finished.|
|`cancelled`|Whether the simulation ended with a cancellation.|
|`failed`|Whether the simulation ended with a failure (including cancellation).|
|`force_stopped`|Whether the simulation ended with a force-stop by the process (TODO: needs fixing).|
|`config`|Config kwargs used to make the Simulation.|
|`start_kwargs`|Config kwargs used when starting the Simulation.|
|`sim_type_name`|True type name for the started Simulation.|
|`sim_module_name`|Module name containing the Simulation type.|

### `sim_status`
|column|description|
|---|---|
|`id`|**Primary key.** Unique key for the status posting.|
|`sim_id`|**Foreign Key (`simulations`).** Reference to simulation to which this status belongs.|
|`time`|Datetime when this status was generated.|
|`code`|Enum defining the status type (SUCCESS=0, FAIL=1, INFO=2).|
|`subcode`|More freeform int code defining other status information (NONE=0, ERROR=1, STOPPED=2).|
|`details`|Information string describing the status.|
|`error_trace`|Optional stack trace if error.|

### `api_calls`
|column|description|
|---|---|
|`id`|**Primary key.** Unique key for the call.|
|`name`|API call endpoint name.|
|`time`|Datetime of call.|
|`code`|TODO: TBD|
|`details`|TODO: TBD|

## ProjectManager
The `ProjectManager` is a singleton that should be accessed when attempting to retrieve database results or calculate paths to project-wide or simulation-specific folders. Typically, all necessary database updates happen through the abstracted `SimulationTracker`. Some of the important calls to know about are:
|call|description|
|---|---|
|`ProjectManager.project_folder()`|Returns the base project directory path.|
|`ProjectManager.sims_folder()`|Returns the path to `sims/` folder.|
|`ProjectManager.db_folder()`|Returns the path to `db/` folder.|
|`ProjectManager.resources_folder()`|Returns the path to `resources/` folder.|
|`ProjectManager.db_path()`|Returns the path to simulation database `db/simulations.db`.|

## SimulationRegistry
Like the `ProjectManager`, the `SimulationRegistry` is also meant to be a global singleton class. At its most basic, the `SimulationRegistry` is simply a map that associates a unique key, representing the kind of `Simulation` to create, with the actual `Simulation` type itself. The `SimulationRegistry` also provides support for optional default configurations that are used if a `Simulation` is created without an input argument configuration.

```python
# Example using SimulationRegistry
# Requires gymdash[full] installation

# Import gymdash modules
from gymdash.backend.core.api.models import SimulationStartConfig
from gymdash.backend.core.simulation.manage import SimulationRegistry
from gymdash.backend.core.simulation.examples import StableBaselinesSimulation

# Create a default SimulationStartConfig for
# your Simulation. Here the default display
# name is "test", sim_key is "CartPole-v1",
# and we have some kwargs with "num_steps"=5000.
my_default_config = SimulationStartConfig(
    name="test",
    sim_key="Acrobot-v1",
    kwargs = {
        "num_steps": 5000,
        "env": "Acrobot-v1",
        "episode_trigger": lambda x: x%2==0
    }
)

# Register your custom Simulation with the SimulationRegistry.
# Here I just register the existing StableBaselinesSimulation type
# under another key, in this case "demo". We also associate our
# SimulationStartConfig as a default config.
SimulationRegistry.register(
    "demo",
    StableBaselinesSimulation,
    my_default_config
)

# Makes a new Simulation, does nothing with it yet...
my_sim = SimulationRegistry.make("demo")

# Makes another Simulation of the same StableBaselinesSimulation
# type, but with different configuration settings.
my_sim2 = SimulationRegistry.make("demo", SimulationStartConfig(
    name="test",
    sim_key="CartPole-v1",
    kwargs = {
        "num_steps": 5000,
    }
))
```

## SimulationTracker
<!-- TODO: more information related to SimulationGroups and running custom stuff, I guess. -->
Next, we need a way to launch and track running `Simulations`. That's where the `SimulationTracker` is required. While running GymDash, the `SimulationTracker` is responsible for setting up, creating, and starting `Simulations`, adding callbacks to `Simulations` and `SimulationGroups`, gathering and sending query interactions to `Simulations`, checking for completed or running `Simulations`, sending cancellation requests to `Simulations`, and updating the backend database as `Simulations` are created, stopped, and completed. Typical usecases, however, tend to be creating/starting `Simulations`, adding callbacks, and checking for when they are done.

#### **Check Simulation Doneness**
- `all_done(sim_keys)`: Given a single `Simulation` ID (UUID) or a list of IDs, returns True if all of them have finished running.
- `any_running(sim_keys)`: Given a single `Simulation` ID (UUID) or a list of IDs, returns True if any of them are still running. Opposite of `all_done`.

#### **Create/Start Simulations**
- `create_simulation(to_create)`: Given either a `Simulation` key, a `SimulationStartConfig`, or an existing `Simulation`, creates and returns a tuple containing the ID and a reference to the `Simulation`.
- `create_simulations(to_create)`: Given a list of arguments allowable in `create_simulation`, returns a `SimulationGroup`.
- `start_sim(to_start, **kwargs)`: Given a `Simulation`, starts it (setup + run) using **kwargs as the `Simulation's` start_kwargs.
- `start_sims(to_start, **kwargs)`: Like `start_sim` except on a `SimulationGroup`.

#### **Add Group-wide Callbacks**
- `on_all_done(sim_ids, callback)`: Creates callback that triggers when all simulations in sim_ids complete. Returns the ID for the callback.
- `add_on_all_done(callback_id, callback)`: Appends another callback to the one denoted by callback_id.

### SimulationTracker Example

<!-- TODO: Edit on_all_done and add_on_all_done into just on_all_done after modifying it to just check for the set of Sim IDs instead of requiring a group callback ID? -->
<!-- -TODO: Change SimulationTracker on_all_done to just check for set of IDs instead of producing a callback ID.
-TODO: Add on_any_done to check for the first time any of the simulations completes, only triggering a max of 1 time.
-TODO: Edit TriggerCallback to have a bool that determines whether the trigger can occur multiple times. -->
```python
# Explore SimulationTracker methods with an example

# Import modules
import argparse
import time
import functools
import uuid
from typing import List
from gymdash.backend.project import ProjectManager
from gymdash.backend.core.api.models import SimulationStartConfig
from gymdash.backend.core.simulation.manage import SimulationRegistry, SimulationTracker
from gymdash.start import add_gymdash_arguments

# Example Simulation (Simulations covered later.
# Feel free to skip for now.)
class DemoSimulation(Simulation):
    def __init__(self, config: SimulationStartConfig) -> None:
        super().__init__(config)
        self.runtime = None
        self.polltime = 0
        self._timer = 0
        self.result = None
        self.show_timer = True

    # Pre-run setup logic
    def _setup(self):
        self._check_kwargs_required(
            ["sim_time", "poll_time"],
            "setup",
            **self.config.kwargs
        )
        self.runtime = self.config.kwargs["sim_time"]
        self.polltime = self.config.kwargs["poll_time"]
        self.timer = 0
        self.show_timer = self.config.kwargs["show_timer"] if "show_timer" in self.config.kwargs is not None else True
        self.result = None

    # This is logic that is run on a separate worker thread.
    # _run() is always called on another thread when Simulations
    # are started normally.
    def _run(self) -> None:
        # Wait some amount of time, printing updates as it runs.
        while (self.timer < self.runtime):
            time.sleep(self.polltime)
            if self.show_timer:
                print(f"{self.timer:.2f}/{self.runtime:.2f}")
            self.timer += self.polltime
        self.result = f"DemoSimulation({self.runtime}, {self.polltime}) \
                        completed successfully."

# Helper method
def create_demo_sim():
    return DemoSimulation(SimulationStartConfig(
        name="test",
        sim_key="test",
        kwargs = {
            "sim_time": 2,
            "poll_time": 0.5
        }
    ))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser = add_gymdash_arguments(parser)
    args = parser.parse_args()
    print(args)

    ProjectManager.setup_from_args(args)

    # Register. Note this produces a simulation with different
    # configuration than create_demo_sim
    default_config = SimulationStartConfig(
        name="demo",
        sim_key="demo",
        kwargs = {
            "sim_time": 2,
            "poll_time": 0.1,
            "show_timer": False
        }
    )
    SimulationRegistry.register("demo", DemoSimulation, default_config)

    # Initialize SimulationTracker
    tracker = SimulationTracker()

    # Setup and run a Simulation without the help
    # of the SimulationTracker or SimulationRegistry:
    # 1. Create Simulation
    # 2. Call setup()
    # 3. Call run()
    print("------------------------------------------------------")
    print(f"Starting demo simulation on main thread")
    testsim = create_demo_sim()
    st = time.time()
    testsim.setup()
    testsim.run()
    et = time.time()
    print(testsim.result)
    print(f"Demo simulation finished after {et-st:.2f}s")

    # Handle multiple simulations.
    # Use the SimulationTracker to start pre-made Simulations.
    # Calling tracker.start_sim(...) runs the Simulation on
    # a new thread, allowing execution here to proceed until the
    # waiting loop.
    print("------------------------------------------------------")
    print(f"Starting 2 simulations in SimulationTracker")
    sim1 = create_demo_sim()
    sim2 = create_demo_sim()
    st = time.time()
    id1, _ = tracker.start_sim(sim1)
    id2, _ = tracker.start_sim(sim2)
    while tracker.any_running(id1) or tracker.any_running(id2):
        pass
    et = time.time()
    print(sim1.result)
    print(sim2.result)
    print(f"Simulations finished after {et-st:.2f}s")

    # Handle many Simulations using callbacks.
    # Here we add a callback to each individual Simulation that 
    # prints the result upon Simulation END_RUN.
    # Additionally, we add another callback that triggers when
    # all the Simulations complete which prints all the results
    # again, along with a 2nd that prints "Hooray! All done!".
    # Notice we have to start with on_all_done to get an intial
    # callback group id and then use that to add_on_all_done
    num_sims = 9
    print("------------------------------------------------------")
    print(f"Starting {num_sims} simulations with callback handling")
    ids: List[uuid.UUID] = []
    sims: List[Simulation] = []
    st = time.time()
    for i in range(num_sims):
        sim = create_demo_sim()
        id, _ = tracker.start_sim(sim)
        sim.add_callback(Simulation.END_RUN, functools.partial(
            lambda sim: print(sim.result), sim=sim
        ))
        sim.show_timer = False
        ids.append(id)
        sims.append(sim)
    group_callback_id = tracker.on_all_done(ids, functools.partial(
        lambda simulations: list(map(lambda s: print(s.result), sims)), simulations=sims
    ))
    tracker.add_on_all_done(group_callback_id, lambda: print("Hooray! All done!"))
    while(tracker.any_running(ids)):
        pass
    et = time.time()
    print(f"Done with all {num_sims} sims.")
    print(f"Simulations finished after {et-st:.2f}s")

    # Handle Simulations with a SimulationGroup. These just
    # provide a simpler interface to multiple Simulations for
    # adding callbacks.
    num_sims = 10
    print("------------------------------------------------------")
    print(f"Starting {num_sims} simulations with SimulationGroup")
    st = time.time()
    # Create the SimulationGroup
    sim_group = tracker.create_simulations(["demo" for _ in range(num_sims)])
    # Add callback once all have started
    sim_group.add_on_all_run_start(lambda: print("All sims started"))
    # Add callback to the last Simulation in the group
    sim_group.sims[-1].add_callback(Simulation.END_RUN, functools.partial(lambda sim: print(sim.result), sim=sim_group.sims[-1]))
    # Add callback once all are done
    sim_group.add_on_all_run_end(lambda: print("All sims ended"))
    # Start sims and wait
    tracker.start_sims(sim_group)
    while(sim_group.any_running):
        pass
    et = time.time()
    print(f"Done with all {num_sims} sims.")
    print(f"Simulations finished after {et-st:.2f}s")

```


## SimulationExporter
Once you have finalized your `Simulation` design and are ready to use it from the GymDash frontend, you must create a custom start script using the `SimulationExporter`. The exporter serializes the simulation key and type information into some files from which newly spawned processes read and setup custom `Simulation` types for use. Without the exporter, the new process spawned by the startup routine will not understand what modules your custom `Simulation` types come from.

Call `SimulationExporter.prepare_for_export(...)` for each custom `Simulation` type you want to be accessible from GymDash, and then call `SimulationExporter.export_sims()` to write out the export files. Finally, use the `start(args)` method in the `gymdash.start` module to startup GymDash.

```python
# Imports
import argparse
from gymdash.backend.core.simulation.examples import StableBaselinesSimulation
from gymdash.backend.core.simulation.export import SimulationExporter
from gymdash.start import add_gymdash_arguments, start

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                    prog='GymDash',
                    description='Start GymDash environment and frontend',
                    epilog='')
    parser = add_gymdash_arguments(parser)
    args = parser.parse_args()

    # Export a new kind of simulation with key "my_custom_sim" and type
    # of StableBaselinesSimulation.
    SimulationExporter.prepare_for_export("my_custom_sim", StableBaselinesSimulation)
    SimulationExporter.export_sims()
    # Start gymdash.
    start(args)
```


[Next: Simulations](02-simulations.md)