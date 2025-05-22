import copy
import logging
import os
import traceback
from abc import abstractmethod
from collections import defaultdict
from datetime import datetime
from threading import Lock, Thread
from typing import (Any, Callable, Dict, Iterable, List, Literal, Set, Tuple,
                    Union)
from uuid import UUID, uuid4

from typing_extensions import Self

from gymdash.backend.core.api.models import (ControlRequestDetails, SimStatus,
                                             SimulationStartConfig,
                                             StoredSimulationInfo)
from gymdash.backend.core.utils.kwarg_utils import overwrite_new_kwargs
from gymdash.backend.enums import SimStatusCode, SimStatusSubcode

logger = logging.getLogger(__name__)

class StopSimException(Exception):
    def __init__(self, message, errors=None) -> None:
        super().__init__(message, errors)
        self.errors = errors

class InteractorFlag:
    def __init__(self, default_status: bool=False, default_value: Any=None) -> None:
        self.default_status = default_status
        self.default_value = default_value
        self.reset()

    def reset(self):
        self.value = self.default_value
        self.triggered = self.default_status
        logger.debug(f"InteractorFlag resetting value to default value: {self.default_value}, default status: {self.default_status} (now value=({self.value}), triggered={self.triggered})")

    def trigger_with(self, new_value: Any):
        logger.debug(f"InteractorFlag setting value to new value: {new_value}")
        # traceback.print_stack()
        self.value = new_value
        self.triggered = True
    
    def consume_trigger(self):
        consumed_trigger = self.triggered
        consumed_value = self.value
        self.reset()
        return consumed_value
    
class InteractorFlagChannel:
    def __init__(self) -> None:
        self.incoming               = InteractorFlag()
        self.outgoing               = InteractorFlag()
        self._consume_in_queued     = False
        self._consume_out_queued    = False

    @property
    def has_incoming(self):
        return self.incoming.triggered
    @property
    def has_outgoing(self):
        return self.outgoing.triggered
    
    def set_in(self, value: Any): self.set_incoming(value)
    def set_out(self, value: Any): self.set_outgoing(value)
    def set_incoming(self, value: Any):
        self.incoming.trigger_with(value)
    def set_outgoing(self, value: Any):
        self.outgoing.trigger_with(value)

    # def consume_immediate_in(self) -> Any:
    #     return self.incoming.consume_trigger()
    # def consume_immediate_out(self) -> Any:
    #     return self.incoming.consume_trigger()
    def get_in(self):
        self._consume_in_queued = True
        return (self.incoming.triggered, self.incoming.value)
    def get_out(self):
        self._consume_out_queued = True
        return (self.outgoing.triggered, self.outgoing.value)
    
    def set_out_if_in(self, out_value: Any):
        """
        Triggers outgoing flag and sets its value if the incoming
        flag has been triggered. Treated as an incoming access, and
        consumption of incoming flag is queued.

        Returns:
            True if the outgoing value was set.
            False if the outgoing value was not set.
        """
        if (self.has_incoming):
            self._consume_in_queued = True
            self.set_outgoing(out_value)
            return True
        return False
    def set_in_if_out(self, in_value: Any):
        """
        Triggers incoming flag and sets its value if the outgoing
        flag has been triggered. Treated as an outgoing access, and
        consumption of outgoing flag is queued.
        
        Returns:
            True if the incoming value was set.
            False if the incoming value was not set.
        """
        if (self.has_outgoing):
            self._consume_out_queued = True
            self.set_incoming(in_value)
            return True
        return False
    def set_out_if_in_value(self, out_value: Any, comparison_value: Any):
        """
        Triggers outgoing flag and sets its value if the incoming
        flag has been triggered AND the incoming value matches the comparison.
        Treated as an incoming access, and consumption of incoming
        flag is queued.
        
        Returns:
            True if the outgoing value was set.
            False if the outgoing value was not set.
        """
        if (self.has_incoming):
            self._consume_in_queued = True
            if self.incoming.value == comparison_value:
                self.set_outgoing(out_value)
                return True
        return False
    def set_in_if_out_value(self, in_value: Any, comparison_value: Any):
        """
        Triggers incoming flag and sets its value if the outgoing
        flag has been triggered AND the outgoing value matches the comparison.
        Treated as an outgoing access, and consumption of outgoing
        flag is queued.

        Returns:
            True if the incoming value was set.
            False if the incoming value was not set.
        """
        if (self.has_outgoing):
            self._consume_out_queued = True
            if self.outgoing.value == comparison_value:
                self.set_incoming(in_value)
                return True
        return False

    def reset(self):
        self.reset_outgoing()
        self.reset_incoming()
    def reset_outgoing(self):
        self.outgoing.reset()
    def reset_incoming(self): 
        self.incoming.reset()

    # def update(self):
    #     self.incoming.consume_trigger()
    #     self.outgoing.consume_trigger()
    #     self._consume_in_queued = False
    #     self._consume_out_queued = False

class SimulationInteractor:
    ALL_CHANNELS: Set[str] = set((
        "stop_simulation",
        "progress",
        "custom_query",
    ))

    def __init__(self) -> None:
        # self.stop_simulation = InteractorFlagChannel()
        # self.progress = InteractorFlagChannel()
        self.channels: Dict[str, InteractorFlagChannel] = {
            channel_key:  InteractorFlagChannel() for channel_key in SimulationInteractor.ALL_CHANNELS
        }
        self._channel_locks: Dict[str, Lock] = {
            channel_key:  Lock() for channel_key in SimulationInteractor.ALL_CHANNELS
        }
        self.triggered_in   = []
        self.triggered_out  = []

        self._has_requests = False
        self._requests_lock = Lock()
        self.requests: Dict[str, List[ControlRequestDetails]] = {
            channel_key:  [] for channel_key in SimulationInteractor.ALL_CHANNELS
        }

    @property
    def has_requests(self):
        return self._has_requests
    @property
    def outgoing(self):
        return { channel_key: channel for channel_key, channel in self.channels.items() if channel.outgoing.triggered }
    @property
    def incoming(self):
        return { channel_key: channel for channel_key, channel in self.channels.items() if channel.incoming.triggered }
    
    def _aquire_all_locks(self):
        for lock in self._channel_locks.values():
            lock.acquire()
    def _release_all_locks(self):
        for lock in self._channel_locks.values():
            lock.release()
    def _aquire_locks(self, channel_keys: Iterable[str]):
        for key in channel_keys:
            self._channel_locks[key].acquire()
    def _release_locks(self, channel_keys: Iterable[str]):
        for key in channel_keys:
            self._channel_locks[key].release()
    def _aquire(self, channel_key: str):
        self._channel_locks[channel_key].acquire()
    def _release(self, channel_key: str):
        self._channel_locks[channel_key].release()

    def add_control_request(self, channel_key: str, details: str="", *other_keys) -> bool:
        with self._requests_lock:
            if channel_key in self.requests:
                request = ControlRequestDetails(key=channel_key, details=details, subkeys=[*other_keys])
                self.requests[channel_key].append(request)
                self._has_requests = True
                return True
            else:
                logger.warning(f"Cannot set new control request for channel '{channel_key}'")
                return False
    # def clear_control_requests_for(self, channel_key: str) -> bool:
    #     with self._requests_lock:
    #         if channel_key in self.requests:
    #             self.requests[channel_key].clear()
    #             return True
    #         else:
    #             logger.warning(f"Cannot clear control requests for channel '{channel_key}'")
    #             return False
    def clear_all_control_requests(self):
        with self._requests_lock:
            self._has_requests = False
            for request_list in self.requests.values():
                request_list.clear()
    # def get_control_requests_for(self, channel_key: str) -> List[ControlRequestDetails]:
    #     with self._requests_lock:
    #         if channel_key in self.requests:
    #             return self.requests[channel_key]
    #         else:
    #             logger.warning(f"Cannot get control request for channel '{channel_key}'")
    #             return []
    def get_all_control_requests(self) -> Dict[str, List[ControlRequestDetails]]:
        with self._requests_lock:
            batch = {}
            for channel_key in self.requests.keys():
                # Add requests for channel if any are there
                if len(self.requests[channel_key]) > 0:
                    batch[channel_key] = copy.copy(self.requests[channel_key])
            return batch
            

    # def update(self):
    #     for channel in self.channels.values():
    #         channel.update()
    def reset(self):
        self._aquire_all_locks()
        for channel in self.channels.values():
            channel.reset()
        self._release_all_locks()
    def reset_outgoing_channels(self, channel_keys: Iterable[str]):
        for key in channel_keys:
            if key in self.channels:
                self._aquire(key)
                self.channels[key].reset_outgoing()
                self._release(key)
    def reset_incoming_channels(self, channel_keys: Iterable[str]):
        for key in channel_keys:
            if key in self.channels:
                self._aquire(key)
                self.channels[key].reset_incoming()
                self._release(key)

    def _try_get_channel(self, key):
        if key in self.channels:
            return (True, self.channels[key])
        else:
            return (False, None)

    def get_in(self, channel_key) -> Tuple[bool, Any]:
        found, channel = self._try_get_channel(channel_key)
        return channel.get_in() if found else (False, None)
        
    def get_out(self, channel_key):
        found, channel = self._try_get_channel(channel_key)
        return channel.get_out() if found else (False, None)
    
    def get_all_outgoing_values(self) -> Dict[str, Any]:
        values = {}
        for channel_key, channel in self.channels.items():
            if channel.outgoing.triggered:
                _, value = channel.get_out()
                values[channel_key] = value
        return values
    def get_all_incoming_values(self) -> Dict[str, Any]:
        values = {}
        for channel_key, channel in self.channels.items():
            if channel.incoming.triggered:
                _, value = channel.get_in()
                values[channel_key] = value
        return values
    
    def set_out(self, channel_key: str, out_value: Any):
        found, channel = self._try_get_channel(channel_key)
        if found:
            self._aquire(channel_key)
            channel.set_out(out_value)
            self._release(channel_key)
            
    def set_in(self, channel_key: str, in_value: Any):
        found, channel = self._try_get_channel(channel_key)
        if found:
            self._aquire(channel_key)
            channel.set_in(in_value)
            self._release(channel_key)
            
    def set_out_if_in(self, channel_key: str, out_value: Any) -> bool:
        found, channel = self._try_get_channel(channel_key)
        if found:
            self._aquire(channel_key)
            was_set = channel.set_out_if_in(out_value)
            self._release(channel_key)
            return was_set
        else:
            return False
    def set_in_if_out(self, channel_key: str, in_value: Any) -> bool:
        found, channel = self._try_get_channel(channel_key)
        if found:
            self._aquire(channel_key)
            was_set = channel.set_in_if_out(in_value)
            self._release(channel_key)
            return was_set
        else:
            return False
    def set_out_if_in_value(self, channel_key: str, out_value: Any, comparison: Any):
        found, channel = self._try_get_channel(channel_key)
        if found:
            self._aquire(channel_key)
            was_set = channel.set_out_if_in_value(out_value, comparison)
            self._release(channel_key)
            return was_set
        else:
            return False
    def set_in_if_out_value(self, channel_key: str, in_value: Any, comparison: Any):
        found, channel = self._try_get_channel(channel_key)
        if found:
            self._aquire(channel_key)
            was_set = channel.set_in_if_out_value(in_value, comparison)
            self._release(channel_key)
            return was_set
        else:
            return False
        
class SimulationStreamer:
    def __init__(self) -> None:
        self.log_map:       Dict[str, Any] = {}
        self.key_log_map:   Dict[str, str] = {}
        self._dirty_keys = True
        self._dirty_tag_key_map = True
        self._dirty_key_tag_map = True
        self._cached_keys = []
        self._cached_tag_key_map = {}
        self._cached_key_tag_map = {}
        self._mutex = Lock()
        

    def set_dirty(self):
        self._dirty_keys = True
        self._dirty_tag_key_map = True
        self._dirty_key_tag_map = True
    def key_has_tag(self, key: str, tag: str) -> bool:
        return key in self.get_key_tag_map() and tag in self.get_key_tag_map()[key]
    def tag_has_key(self, tag: str, key: str) -> bool:
        return tag in self.get_tag_key_map() and key in self.get_tag_key_map()[tag]
    def get_all_keys(self) -> List[Tuple[str, str]]:
        """
        Return a list of all stat keys and their associated
        media tags used across all streamers.
        """
        # Use cached version
        if not self._dirty_keys:
            return self._cached_keys
        # Remake cached version
        stat_keys = []
        for streamer in self.streamers():
            stat_keys.extend(streamer.get_stat_keys())
        self._cached_keys = stat_keys
        self._dirty_keys = False
        return self._cached_keys
    def get_tag_key_map(self) -> Dict[str, Set[str]]:
        """
        Return a dictionary mapping each used tag to a
        set of stat keys that are under that tag.
        """
        # Use cached version
        if not self._dirty_tag_key_map:
            return self._cached_tag_key_map
        # Remake cached version
        self._cached_tag_key_map = defaultdict(set)
        keys = self.get_all_keys()
        for key, tag in keys:
            self._cached_tag_key_map[tag].add(key)
        self._dirty_tag_key_map = False
        return self._cached_tag_key_map
    def get_key_tag_map(self) -> Dict[str, Set[str]]:
        """
        Return a dictionary mapping each used key to a
        set of tags that are associated with that key.
        """
        # Use cached version
        if not self._dirty_key_tag_map:
            return self._cached_key_tag_map
        # Remake cached version
        self._cached_key_tag_map = defaultdict(set)
        keys = self.get_all_keys()
        for key, tag in keys:
            self._cached_key_tag_map[key].add(tag)
        self._dirty_key_tag_map = False
        return self._cached_key_tag_map
    
    def get_streamer_for_key(self, key):
        if key in self.key_log_map:
            return self.get_streamer(self.key_log_map[key])
        return None

    def clear(self):
        with self._mutex:
            self.log_map.clear()
            self.key_log_map.clear()
            self._cached_tag_key_map.clear()
            self._cached_keys.clear()
            self.set_dirty()

    def get_streamer(self, log_key: str):
        with self._mutex:
            return self.log_map[log_key] if log_key in self.log_map else None

    def _get_or_register(self, log_key: str, streamer: Any):
        retrieved = self.get_streamer(log_key)
        if retrieved:
            print(f"Got existing streamer from '{log_key}'")
            return retrieved
        else:
            if self.register(log_key, streamer):
                print(f"Registered new streamer to '{log_key}'")
                return streamer
            else:
                raise ValueError(f"No existing streamer with name '{log_key}' found, but unable to register")
            
    def get_or_register(self, streamer: Any):
        return self._get_or_register(streamer.streamer_name, streamer)
    
    def register(self, log_key: str, streamer: Any):
        with self._mutex:
            if (log_key in self.log_map):
                return False
            self.log_map[log_key] = streamer
            # Add stat keys from the streamer to my map
            for stat_key, tag in streamer.get_stat_keys():
                self.key_log_map[stat_key] = log_key
            print(f"Register streamer '{log_key}'")
            self.set_dirty()
            logger.info("Set SimulationStreamer dirty")
            return True
    
    def items(self):
        """Return an array of references to registered Streamer keys and Streamers."""
        with self._mutex:
            return [x for x in self.log_map.items()]
    
    def streamers(self):
        """Return an array of references to registered Streamers."""
        with self._mutex:
            return [x for x in self.log_map.values()]

class Simulation():

    START_SETUP = "start_setup"
    END_SETUP   = "end_setup"
    START_RUN   = "start_run"
    END_RUN     = "end_run"

    def __init__(self, config: SimulationStartConfig) -> None:
        self.config: SimulationStartConfig      = config
        self.thread: Thread                     = None
        self.start_kwargs                       = None
        self.interactor                         = SimulationInteractor()
        self.streamer                           = SimulationStreamer()
        self.kwarg_defaults                     = self.create_kwarg_defaults()
        self._callback_map: Dict[str, List[Callable[[Simulation], Simulation]]] = {
            Simulation.START_SETUP:     [],
            Simulation.END_SETUP:       [],
            Simulation.START_RUN:       [],
            Simulation.END_RUN:         [],
        }
        self.force_stopped: bool                = False
        self.from_disk: bool                    = False

        self._meta_mutex: Lock                  = Lock()
        self._meta_cancelled: bool              = False
        self._meta_failed: bool                 = False
        self._meta_statuses: List[SimStatus]    = []
        self._meta_num_saved_statuses: int      = 0

        self._meta_create_time                  = datetime.now()
        self._meta_start_time                   = None
        self._meta_end_time                     = None

        self._project_info_set: bool            = False
        self._project_sim_id: UUID              = None
        self._project_sim_base_path: str        = None

    @property
    def sim_path(self) -> Union[str, None]:
        if self._project_info_set:
            return os.path.join(self._project_sim_base_path, str(self._project_sim_id))
        else:
            return None
        
    def fill_from_stored_info(self, info: StoredSimulationInfo):
        logger.debug(f"fill_from_stored_info config: {info.config}")
        self.from_disk = True
        self._project_sim_id = info.sim_id
        self.start_kwargs = info.start_kwargs
        self._meta_cancelled = info.cancelled
        self._meta_failed = info.failed
        self._meta_create_time = info.created
        self._meta_start_time = info.started
        self._meta_end_time = info.ended
        self.config = info.config
        self.force_stopped = info.force_stopped
        
    # Maybe something like you call this when you get or register streamer
    # (new callback wrapper around streamer.get_or_register?)
    def create_streamers(self, config: SimulationStartConfig = None, kwargs: Dict[str, Any] = None):
        if config is None or config.kwargs is None:
            config_kwargs = {}
        else:
            config_kwargs = config.kwargs
        if kwargs is None:
            kwargs = {}
        self._create_streamers(
            self._overwrite_new_kwargs(self.kwarg_defaults, config_kwargs, kwargs)
        )
    @abstractmethod
    def _create_streamers(self, kwargs: Dict[str, Any]):
        pass

    def _to_every_x_trigger(self, value):
        if isinstance(value, int):
            if (value <= 0): return lambda x: False
            return lambda x: x%value==0
        else:
            return value

    def set_project_info(self, project_sim_base_path: str, project_resources_path: str, sim_id: UUID):
        """
        Sets specific information that is only accessible from outside
        a Simulation.

        Args:
            project_sim_base_path: Path to the folder where individual
                simulation folders are stored.
            sim_id: The ID of this Simulation as created elsewhere
        """
        self._project_info_set      = True
        self._project_sim_id        = sim_id
        self._project_sim_base_path = project_sim_base_path
        self._project_resources_path= project_resources_path
    
    def was_cancelled(self):
        with self._meta_mutex:
            return self._meta_cancelled
    def set_cancelled(self) -> None:
        with self._meta_mutex:
            self._meta_cancelled = True
    def add_error_details(self, new_error: str) -> None:
        self.add_status(SimStatus(
            code=SimStatusCode.FAIL,
            subcode=SimStatusSubcode.ERROR,
            details=new_error,
            error_trace=traceback.format_exc()
        ))
    def add_status(self, status: SimStatus):
        status.time = datetime.now()
        with self._meta_mutex:
            self._meta_statuses.append(status)
    def retrieve_new_statuses(self) -> List[SimStatus]:
        with self._meta_mutex:
            new_statuses = self._meta_statuses[self._meta_num_saved_statuses:]
            self._meta_num_saved_statuses = len(self._meta_statuses)
            return new_statuses

    def create_kwarg_defaults(self) -> Dict[str, Any]:
        return {}

    @property
    def name(self) -> str:
        return self.config.name
    @property
    def is_done(self) -> bool:
        return  self.from_disk or \
                self.force_stopped or \
                self.thread is None or \
                not self.thread.is_alive()

    def _overwrite_new_kwargs(self, old_kwargs, *args) -> Dict[str, Any]:
        """
        Returns a unified dictionary of keyword arguments where each subsequent
        keyword dictionary adds its own values to the old dictionary,
        overwriting existing values at matching keys.

        Args:
            old_kwargs: Old dict of keyword arguments to override.
            *args: Tuple of new keyword arguments to apply to the old.
        Return:
            new_kwargs: New dictionary containing unified kwargs
        """
        return overwrite_new_kwargs(old_kwargs, *args)
    
    def _check_kwargs_required(self, req_args: List[str], method_name, **kwargs):
        for arg in req_args:
            if arg not in kwargs:
                logger.error(f"Argument '{arg}' not provided for method '{method_name}' of {type(self)}")
                raise ValueError(f"Argument '{arg}' not provided for method '{method_name}' of {type(self)}")
    def _check_kwargs_optional(self, req_args: List[str], method_name, **kwargs):
        for arg in req_args:
            if arg not in kwargs:
                logger.warning(f"Argument '{arg}' not provided for method '{method_name}' of {type(self)}")
    
    def false_start(self, **kwargs):
        """
        Same as start, but sets from_disk flag to true so actual simulation
        logic does NOT run during call to run()
        """
        self.from_disk = True
        self.start(**kwargs)

    def start(self, **kwargs):
        """
        Begins the simulation. Invokes setup() on this thread, then run()
        on a worker thread.
        """
        self.start_kwargs = kwargs
        self.setup(**kwargs)
        self.thread = Thread(target=self.run)
        self.thread.start(**kwargs)
        return self.thread

    def reset_interactions(self):
        self.interactor.reset()

    def get_outgoing_values(self) -> Dict[str, Any]:
        channel_values = self.interactor.get_all_outgoing_values()
        # Meta values that don't need interaction channels
        channel_values["is_done"]       = self.is_done
        channel_values["cancelled"]     = self._meta_cancelled
        channel_values["failed"]        = self._meta_failed
        # channel_values["error_details"] = self._meta_error_details
        channel_values["error_details"] = self._meta_statuses
        return channel_values

    # def trigger_as_query(self, incoming_interactions: SimulationInteractionModel) -> Dict[str, Any]:
    #     for channel_key, value in incoming_interactions:
    #         self.interactor.set_in(channel_key, value)

    def _on_setup_start_callback(self) -> List[Callable[[], Self]]:
        return self._callback_map[Simulation.START_SETUP]
    def _on_setup_end_callback(self) -> List[Callable[[], Self]]:
        return self._callback_map[Simulation.END_SETUP]
    def _on_run_start_callback(self) -> List[Callable[[], Self]]:
        return self._callback_map[Simulation.START_RUN]
    def _on_run_end_callback(self) -> List[Callable[[], Self]]:
        return self._callback_map[Simulation.END_RUN]
    
    def add_callback(
        self,
        event: Literal["start_setup", "end_setup","start_run","end_run"],
        callback: Callable[[Self], Self]
    ):
        if event not in self._callback_map:
            raise ValueError(f"Cannot add callback of event type '{event}'")
        self._callback_map[event].append(callback)

    def get_callbacks(
        self,
        event: Literal["start_setup", "end_setup","start_run","end_run"]
    ) -> Callable[[Self], Self]:
        if event not in self._callback_map:
            raise ValueError(f"Cannot add callback of event type '{event}'")
        return self._callback_map[event]
    
    def trigger_callbacks(
        self,
        event: Literal["start_setup", "end_setup","start_run","end_run"]
    ) -> Self:
        callbacks = self.get_callbacks(event)
        logger.debug(f"Simulation triggering {len(callbacks)} callbacks for '{event}'.")
        for callback in callbacks:
            callback()

    def setup(self, **kwargs) -> None:
        logger.debug(f"Simulation setup() kwargs: {kwargs}.")
        # Start setup callbacks
        try:
            self.trigger_callbacks(Simulation.START_SETUP)
        except Exception:
            logger.exception(f"Exception when running Simulation '{Simulation.START_SETUP}' callbacks.")
        # Setup
        try:
            self._setup(**kwargs)
        except Exception:
            logger.exception(f"Exception when calling Simulation _setup().")
        # End setup callbacks
        try:
            self.trigger_callbacks(Simulation.END_SETUP)
        except Exception:
            logger.exception(f"Exception when running Simulation '{Simulation.END_SETUP}' callbacks.")

    def run(self, **kwargs) -> None:
        logger.debug(f"Simulation run() kwargs: {kwargs}.")
        # Start run callbacks
        try:
            self.trigger_callbacks(Simulation.START_RUN)
        except Exception:
            logger.exception(f"Exception when running Simulation '{Simulation.START_SETUP}' callbacks.")
        # Run
        try:
            # ONLY RUN IF YOU WERE NOT LOADED FROM DISK
            if not self.from_disk:
                self._meta_start_time = datetime.now()
                self._run(**kwargs)
        except Exception:
            logger.exception(f"Exception when calling Simulation _run().")
        # End run callbacks
        self._meta_end_time = datetime.now()
        self.trigger_callbacks(Simulation.END_RUN)
        # If we are here and the stop_simulation flag has been raised
        # and not dealt with, then we can deal with it now.
        # Make sure it's after all the callbacks so we don't have any
        # funny business.
        self.interactor.set_out_if_in("stop_simulation", True)
    
    @abstractmethod
    def _setup(self, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def _run(self, **kwargs) -> None:
        raise NotImplementedError
    
    def close(self) -> None:
        pass