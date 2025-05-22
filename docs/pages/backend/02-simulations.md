# Simulations
The backbone (and entire functionality) of GymDash revolves around the `Simulation`. Simulations are just an abstraction that is wrapped around any kind of process that can be run, stopped, and interacted with. The initial intention is to have Simulations wrap long-running processes like machine learning, but they also work for more arbitrary simulations.

## Simulation Class
<!-- TODO: 2 types of _create_streamers, 1 for during running, 1 for non-running sim from disk. -->
<!-- TODO: Unify streamers under a base class. Same with StreamableStat. Maybe more of an interface? ABC -->
The `Simulation` class is a base class that must be subclassed for proper use. `Simulations` have 3 abstract methods that must be implemented for frontend use:
- `_create_streamers(kwargs)`: This method exists only for recreating data streamers for `Simulations` that are no longer running and have been retrieved from disk.
- `_setup(**kwargs)`: This method runs any setup logic on the `Simulation` before running. This logic is performed on the starting thread and not the run thread.
- `_run(**kwargs)`: This method contains the main running logic for the `Simulation`.
```python
class Simulation:
    # Lots of other stuff ...

    # Required implementations
    @abstractmethod
    def _create_streamers(self, kwargs: Dict[str, Any]):
        pass

    @abstractmethod
    def _setup(self, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def _run(self, **kwargs) -> None:
        raise NotImplementedError

    # Optional overrides
    def create_kwarg_defaults(self) -> Dict[str, Any]:
        return {}
```

### SimulationInteractor
An important aspect of GymDash is interactivity. For individual `Simulations`, this is managed by the `SimulationInteractor`. Each `Simulation` has its own `SimulationInteractor` which consists of several `InteractorFlagChannel`s and `ControlRequestDetails`. An `InteractorFlagChannel` is basically a 2-way street associated with some key. When the user provides a query interaction, the `SimulationTracker` in charge tells each `SimulationInteractor` to "set" the "incoming" channel with some optional data. As each of the `Simulation`s run in their own thread, they may check these incoming channels and, if flagged, perform some task and "set" the "outgoing" channel of the `InteractorFlagChannel` with data to indicate that it has been acted upon. The most common methods for the `SimulationInteractor` are:

|method|description|
|---|---|
|`get_in`| Given a channel key returns a tuple containing the incoming flag status and incoming value of the channel if it exists, otherwise `(False, None)`. |
|`get_out`| Given a channel key returns a tuple containing the outoging flag status and outgoing value of the channel if it exists, otherwise `(False, None)`. |
|`set_in`| Given a channel key and a value, sets the incoming flag and value for the channel if it exists. |
|`set_out`| Given a channel key and a value, sets the outgoing flag and value for the channel if it exists. |
|`set_out_if_in`| Given a channel key and a value, sets the outgoing value for the channel if it exists AND the incoming flag is triggered. |

Less common methods:
|method|description|
|---|---|
|`set_in_if_out`| Given a channel key and a value, sets the incoming value for the channel if it exists AND the outgoing flag is triggered. |
|`set_out_if_in_value`| Given a channel key, a value, and a comparison value, sets the outgoing value for the channel if it exists AND the incoming flag is triggered AND the comparison value matches the incoming channel value. |
|`set_in_if_out_value`| Given a channel key, a value, and a comparison value, sets the incoming value for the channel if it exists AND the outgoing flag is triggered AND the comparison value matches the outgoing channel value. |


#### Fulfilling Query Interactions (Implementation Details)
Various parts of each query may be fulfilled over time, so the `SimulationTracker` keeps a nested dictionary that tracks all of the query interactions for each `Simulation`. As query interactions are gathered and returned (or time out), the `SimulationTracker` calculates which of the `Simulation`'s channels need to be reset (have their flag set to False). An incoming flag represents something that the `Simulation` should act upon and an outgoing flag represents the output of that act that should be gathered and sent to the frontend.

We don't want to reset an incoming flag immediately if another query interaction has yet to gather information from that flag. We don't want to reset an outgoing flag immediately again because another query interacion might not have read that data. Instead, at the end of each query interaction, the channel keys from the interaction are checked against the other current interactions open for the `Simulation`, and if no interactions are open for that key, then the incoming and outgoing channels can be reset.

<!-- TODO: Make sure thread safe. -->
Also, since `SimulationInteractor`s utilize a mutex to lock channels as they are used, they should be thread safe, and channels should maintain one change or access at a time.

### SimulationStreamer
<!-- TODO: Unite streamers and streamable stats -->
Next, each `Simulation` has their own `SimulationStreamer`. All data that should be sent to the frontend should be managed by the `SimulationStreamer`. `SimulationStreamer`s contain various `Streamer`s which each contain some number of `StreamableStat`s. The `Streamer` manages any number of a similar type of `StreamableStat` and provides an interface to access the data in the `StreamableStat`s as well utility methods for getting associated keys (names) of stats. Each `StreamableStat` provides the `get_recent()` and `get_values()` methods:
- `get_recent`: Return only the datapoints generated **since the last call to `get_recent`**.
- `get_values`: Return all the datapoints generated by this stat.

Currently, the 2 main Streamers, `TensorboardStreamer` and `MediaFileStatLinker`, are not derived from nor implement the `Streamer`. Similarly, `TensorboardStreamableStat` and `MediaLinkStreamableStat` also do not subclass `StreamableStat`, though in all of these cases, they do define enough of the same methods to be useable by the `SimulationTracker`.
Both `Streamer` and `StreamableStat` will likely be turned into just an interface in the future.

#### TensorboardStreamableStat
`TensorboardStreamableStat` uses a tensorboard log file, an EventAccumulator, and an internal index to keep track of what data from the log file hasn't yet been sent to the frontend.
#### MediaLinkStreamableStat
`MediaLinkStreamableStat` checks a given directory for files matching a certain filename pattern and decodes a step value from each matching filename, using each file's last modification datetime to help determine which files are new and should be sent to the frontend.

Work in progress...

### Using Custom Simulations
From within a `Simulation` subclass, use the following fields:
- `_project_sim_id`: Get the UUID from within the `Simulation`
- `_project_sim_base_path`: Get path to the `Simulation`-specific resource folder. Use this to compute log folders e.g. tensorboard log path.
- `_project_resources_path`: Get path to the project-specific resource folder. Use this to compute paths for things like shared datasets or files.

#### Common Kwarg Usage
When implementing a `Simulation`'s `_setup` or `_run` methods, you will frequently want to combine class default kwargs with kwargs from both the `SimulationStartConfig` and the method input kwargs. To do so, you can use `self._overwrite_new_kwargs(...kwarg_dicts)` to combine all the kwargs in order, with later kwarg inputs overwriting old ones and returning a new dictionary of kwargs to use in the method:

```python
kwargs = self._overwrite_new_kwargs(self.kwarg_defaults, self.config.kwargs, kwargs)
```

#### Common Interactor Usage
For most `Simulations`, having the ability to stop the simulation is a big part of the interactivity allowed by GymDash. This is done through the `SimulationInteractor`, specifically with the `progress` interactor channel. You may set this outgoing channel and manually set some flag that triggers a stop in your run logic, or you may raise the StopSimException if your run logic can catch it.

Another common quality-of-life feature supported by GymDash is the progress indicator. To update the progress, you can flag the outgoing `progress` channel and provide a tuple containing the numerator and denominator of your progress, e.g. (current_step, total_steps). The following callback used in `StableBaselinesSimulation` is shows an example of both providing output information (`progress`) and allowing incorporation of incoming data (`stop_simulation`).

```python
# Here is the SimulationInteractionCallback, a stable baselines
# callback used in StableBaselinesSimulation to signal when the
# process should be stopped. Some other logic has been omitted
# from this example to emphasize the stopping logic.
class SimulationInteractionCallback(BaseCallback):
    def __init__(self, simulation: Simulation, verbose: int = 0):
        super().__init__(verbose)
        self.simulation = simulation
        self.curr_timesteps = 0
        self.total_timesteps = 0
    
    # Empty methods omitted...

    @property
    def interactor(self):
        return self.simulation.interactor

    def _on_training_start(self) -> None:
        # From the ProgressBarCallback
        self.total_timesteps = self.locals["total_timesteps"] - self.model.num_timesteps

    def _on_step(self) -> bool:
        # HANDLE OUTGOING INFORMATION
        # Return progress value equivalent to the one used in ProgressBarCallback
        self.curr_timesteps += self.training_env.num_envs
        self.interactor.set_out_if_in("progress", (self.curr_timesteps, self.total_timesteps))
        # HANDLE INCOMING INFORMATION
        # ------------------------------------
        # Check if the stop_simulation channel has an incoming flag.
        # If so, then we should stop.
        # Stable Baselines callbacks allow you to return False from _on_step
        # if the process should end.
        # ------------------------------------
        # Note, set_out_if_in returns a boolean representing whether the
        # checked channel has an incoming flag and sets the corresponding
        # outgoing flag if so.
        if self.interactor.set_out_if_in("stop_simulation", True):
            self.simulation.set_cancelled()
            return False
        return True
```

#### Common Streamer Usage
Utilize the `SimulationStreamer` at `self.streamer` to provide a way to get data from the backend to the frontend. If using tensorboard, you will likely just need to register the `TensorboardStreamer`. If you also create media files, you may need a `MediaFileStatLinker` with one or more `MediaLinkStreamableStat`s.

```python
class StableBaselinesSimulation(Simulation):
    # Other methods omitted...

    def __init__(self, config: SimulationStartConfig):
        super().__init__(config)
        # ...
        # Create a dict mapping tag types to stat names
        # Here we want to send episode reward and learning rates
        # recorded in stable baselines simulation to the frontend.
        self.tb_tag_key_map = {
            stat_tags.TB_SCALARS: ["rollout/ep_rew_mean", "train/learning_rate"],
        }

    def _run(self, **kwargs):
        # Gather kwargs
        kwargs = self._overwrite_new_kwargs(self.kwarg_defaults, self.config.kwargs, kwargs)

        # Setting up logic...
        # ...

        # Making the environment
        env = gym.make(...)

        # Use a special TensorboardStreamWrapper which is TensorboardStreamer
        # in a environment wrapper format.
        # Note we also call self.streamer.get_or_register to register the streamer
        # under the streamer's "streamer_name" which is defined based on the
        # streamer's implementation.
        # This streamer will contain TensorboardStreamableStats for the stats:
        #   rollout/ep_rew_mean
        #   train/learning_rate
        env = self.streamer.get_or_register(TensorboardStreamWrapper(
            env,
            tb_path,
            self.tb_tag_key_map
        ))
        # Register another Streamer, this time a MediaFileStatLinker.
        # Provide a streamer_name and a list of MediaLinkStreamableStats.
        self.streamer.get_or_register(MediaFileStatLinker(
            "media_" + tb_path,
            [
                # Each stat should define:
                #   1. The stat name.
                #   2. The stat tag/type.
                #   3. The directory to look in for media files.
                #   4. The regex expression to match relevant media files to this stat.
                #   5. The function used to parse an integer step from the filename (str -> int)
                MediaLinkStreamableStat(
                    "episode_video",
                    stat_tags.VIDEOS,
                    video_path,
                    r"rl-video-(episode|step)-[0-9]+_[0-9]+\.mp4",
                    lambda fname: int(fname.split("_")[-1][:-4])
                )
            ]
        ))
        
        # Other logic...
        # ...
```

#### Common Try/Except Usage
You will likely want to wrap your setup and run logic in a `try/except` block where the Exception status is logged and the `Simulation` is stopped and marked as a failure. You do not have to do this, though. Maybe you have some restart logic or maybe you're fine just letting it break, it's up to you.
<!-- TODO: Change model.save() -->
```python
class StableBaselinesSimulation(Simulation):
    # Other methods omitted...

    def _run(self, **kwargs):
        # Gather kwargs
        kwargs = self._overwrite_new_kwargs(self.kwarg_defaults, self.config.kwargs, kwargs)

        # Setting up streamers, environment, model, tensorboard, etc...
        # ...

        # Create instance of our callback. The callback will set
        # self.was_cancelled = True if it was cancelled.
        sim_interact_callback = SimulationInteractionCallback(self)
        try:
            # Launch model learning
            self.model.learn(total_timesteps=num_steps, progress_bar=False, callback=sim_interact_callback)
            # Check cancellation status
            was_cancelled = self.was_cancelled()
            if was_cancelled:
                # Set failure status is cancelled
                self.add_status(SimStatus(
                    code=SimStatusCode.FAIL,
                    subcode=SimStatusSubcode.STOPPED,
                    details="Simulation stopped."
                ))
            else:
                # Set success status if completed properly
                self.add_status(SimStatus(
                    code=SimStatusCode.SUCCESS,
                    details="Simulation successfully run."
                ))
        # Other implementations could raise a StopSimException instead.
        # We can catch them and treat them as a failure here if so.
        except StopSimException as se:
            self._meta_failed = True
            self.add_status(SimStatus(
                code=SimStatusCode.FAIL,
                subcode=SimStatusSubcode.STOPPED,
                details="Simulation stopped."
            ))
        # If we got some other error, mark it as a failure
        # and log the error status.
        except Exception as e:
            self._meta_failed = True
            self.add_error_details(str(e))
        
        # Other teardown logic...
        # ...
```

#### Common Custom Query Usage
Only a couple explicit interaction channels are specified in `SimulationInteractor`: `stop_simulation` and `progress`. Everything else is handled by the `custom_query` channel. This channel operates like a normal `InteractorFlagChannel`, but should be handled with a bit more care. The values set on this channel should typically be dictionaries containing the custom information you wish to act on or return. Current examples only use this for providing custom data to the Simulation, but sending custom data back to the frontend should also be possible.
<!-- TODO: Check sending custom data from custom_query to the frontend. -->

```python
class CustomControlSimulation(Simulation):
    # Other methods omitted...

    def _run(self, **kwargs):
        # Other setup...
        # ...

        # Here we check for a special interactive mode. If we are
        # in this mode, then we enter a loop that sends a request to
        # the frontend for a custom_query that contains the key "continue".
        # This loop periodically checks incoming values in the custom_query
        # channel and unpacks them, setting used values along the way.
        # Once it receives a query with the "continue" key, it moves on.
        if interactive:
            self.interactor.add_control_request("custom_query", interactive_text)
            while True:
                # HANDLE INCOMING INFORMATION
                if self.interactor.set_out_if_in("stop_simulation", True):
                    self.set_cancelled()
                    writer.close()
                    return
                triggered, custom = self.interactor.get_in("custom_query")
                if triggered:
                    if "poll_period" in custom:
                        poll_period = custom["poll_period"]
                    if "total_runtime" in custom:
                        total_runtime = custom["total_runtime"]
                    if "pause_points" in custom:
                        pause_points = custom["pause_points"]
                    if "other_kwargs" in custom:
                        other_kwargs = custom["other_kwargs"]
                    self.interactor.set_out("custom_query", custom)
                    if "continue" in custom:
                        break
                    else:
                        time.sleep(0.1)

        # Process the rest of the simulation...
```

#### Loading Old Simulations
When the backend is restarted, there is currently no way to "restart" a `Simulation`, though the "restart" is a work in progress. Instead, it does do a minimal setup to allow data streaming when loading from disk. Because the `SimulationTracker` is responsible for interfacing between the `ProjectManager`'s database and `Simulations`, it is also responsible for providing each individual `Simulation` with project-related information during setup such as the project resources folder and simulation resources folder. Other meta information that `Simulations` typically accumulate over their runtime is also loaded from disk:
|field|description|
|---|---|
|`from_disk`| Set to True when loaded from disk. Prevents _run() logic from running. |
|`force_stopped`| One flag checked to determine if simulation is done. |
|`config`| `SimulationStartConfig` used to create the `Simulation`. |
|`start_kwargs`| kwargs used when starting/running the `Simulation`. |
|`_project_sim_id`| UUID loaded from disk. |
|`_meta_cancelled`| Whether `Simulation` was cancelled. |
|`_meta_failed`| Whether `Simulation` failed. |
|`_meta_create_time`| Datetime when `Simulation` created. |
|`_meta_start_time`| Datetime when `Simulation` started. |
|`_meta_end_time`| Datetime when `Simulation` ended. |

Finally, `create_streamers` is also called on loaded `Simulations`, allowing data to be streamed to the GymDash frontend. This allows you to see data from old processing runs.

## Template Examples:
Example Simulations in module `gymdash.backend.core.simulation.examples`.
|key|type|description|
|---|---|---|
|stable_baselines|StableBaselinesSimulation| Runs a stable baselines simulation by creating varied Gymnasium environments and running stable baselines algorithms to teach models. |
|custom_control|CustomControlSimulation| Runs a simulation that feigns processing for some total runtime. Pause points can be specified which require the user to send custom_query's to the simulation to continue. |
|example_ml|MLSimulation| (Subject to change) Trains and validates a simple CNN classifier on the MNIST dataset. |
### Stable Baselines
#### Config Arguments:
|arg|type|default|description|
|---|---|---|---|
|`num_steps`|int|`5000`|Minimum steps to run the simulation.|
|`episode_trigger`|int|`-`|Records a video every X episodes.|
|`step_trigger`|int|`-`|Records a video every X steps.|
|`video_length`|int|`0`|Number of frames in recorded videos. 0 for uncapped.|
|`fps`|int|`30`|Frames-per-second of the recorded videos.|
|`env`|str|`"CartPole-v1"`|Gymnasium environment name.|
|`policy`|str|`"MlpPolicy"`|Stable baselines policy name.|
|`algorithm`|str|`"ppo"`|Stable baselines algorithm name.|
|`algorithm_kwargs`|dict|`{}`|Kwargs passed into Stable baselines algorithm.|
#### Outputs:
|key|type|description|
|---|---|---|
|`rollout/ep_rew_mean`|`"scalars"`|Reward for training episodes.|
|`train/learning_rate`|`"scalars"`|Learning rate over time.|
|`episode_video`|`"videos"`|Episode recordings.|

### Custom Control
#### Config Arguments:
|arg|type|default|description|
|---|---|---|---|
|`interactive`|bool|`False`|Whether to run in interactive mode.|
|`poll_period`|float|`0.5`|How often to record a data point.|
|`total_runtime`|float|`30`|Total amount of time the simulation runs with no pauses.|
|`pause_points`|float[]|`[]`|List of times when the simulation will pause and wait for user input.|
|`other_kwargs`|dict|`{}`|Unused.|
#### Outputs:
|key|type|description|
|---|---|---|
|`my_number`|`"scalars"`|Number that grows over time with small random variations.|

### Machine Learning (PyTorch)
Work in progress...
#### Config Arguments:
|arg|type|default|description|
|---|---|---|---|
|`train`|bool|`True`|Whether to train the model.|
|`val`|bool|`False`|Whether to run validations while training the model.|
|`test`|bool|`False`|Whether to run testing on the trained model.|
|`inference`|bool|`False`|(Work in progress...) Whether to open up the model for interactive inference.|
|`train_kwargs`|dict|`{}`|Training kwargs. Currently, only `epochs` is supported.|
|`val_kwargs`|dict|`{}`|(Work in progress...) Validation kwargs.|
|`test_kwargs`|dict|`{}`|(Work in progress...) Testing kwargs.|
|`inference_kwargs`|dict|`{}`|(Work in progress...) Inference kwargs.|
#### Outputs:
|key|type|description|
|---|---|---|
|`loss/train`|`"scalars"`|Training loss.|
|`loss/val`|`"scalars"`|Validation loss.|
|`acc/val`|`"scalars"`|Validation classification accuracy.|
|`example_outputs`|`"images"`|Sample of classified outputs taken every X training steps.|