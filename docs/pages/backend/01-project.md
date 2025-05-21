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
(Subject to change)

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
|`code`|TBD|
|`details`|TBD|

## ProjectManager
The `ProjectManager` is a singleton that should be accessed when attempting to retrieve database results or calculate paths to project-wide or simulation-specific folders. Typically, all necessary database updates happen through the abstraced `SimulationTracker`. Some of the important calls to know about could be:
|call|description|
|---|---|
|`ProjectManager.project_folder()`|Returns the base project directory path.|
|`ProjectManager.sims_folder()`|Returns the path to `sims/` folder.|
|`ProjectManager.db_folder()`|Returns the path to `db/` folder.|
|`ProjectManager.resources_folder()`|Returns the path to `resources/` folder.|
|`ProjectManager.db_path()`|Returns the path to simulation database `db/simulations.db`.|

## SimulationRegistry
Like the `ProjectManager`, the `SimulationRegistry` is also meant to be a global singleton class. At its most basic, the `SimulationRegistry` is simply a map that associates a unique key, representing the kind of `Simulation` to create, with the actual `Simulation` type itself. The `SimulationRegistry` also provides support for optional default configurations that are used if a `Simulation` is created with not input argument configuration.

`static register()`
- Args:
    - `key` (`str`): Registered name of the simulation type to register
    - `creator` (`Callable[[SimulationStartConfig], Simulation]`): Initializer/type of the Simulation to register
    - `start_config` (`Union[SimulationStartConfig, None] = None`): Optional default configuration

```python
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
# type, but with configuration settings.
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
Next, we need a way to launch and track running `Simulations`. That's where the `SimulationTracker`

To test a Simulation, you can create a brief script that initializes the `ProjectManager` to your default `./gymdash-projects/` project folder, registers a new `Simulation` in `SimulationRegistry`, and invokes `start_sim` on a new `SimulationTracker` instance.

## SimulationExporter
Once you have finalized your `Simulation` design and are ready to use it from the GymDash frontend, you must create a custom start script using the `SimulationExporter`. The exporter serializes the simulation key and type information into some files from which newly spawned processes read and setup custom `Simulation` types for use. Without the exporter, the new process spawned by the startup routine will not understand what modules your custom `Simulation` types come from.

Call `SimulationExporter.prepare_for_export(...)` for each custom `Simulation` type you want to be accessible from GymDash, and then call `SimulationExporter.export_sims()` to write out the export files. Finally, use the `start(args)` method in the `gymdash.start` module to startup GymDash.

Project Layout, databases, etc.


[Next: Simulations](02-simulations.md)