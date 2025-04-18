import logging
import os
from abc import abstractmethod
from datetime import datetime
from threading import Lock, Thread
from typing import (Any, Callable, Dict, Iterable, List, Literal, Set, Tuple,
                    Union)
from uuid import UUID, uuid4

from typing_extensions import Self

from gymdash.backend.core.api.models import SimulationStartConfig

logger = logging.getLogger(__name__)

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

    def get_in(self, channel_key):
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
        self.kwarg_defaults                     = self.create_kwarg_defaults()
        self._callback_map: Dict[str, List[Callable[[Simulation], Simulation]]] = {
            Simulation.START_SETUP:     [],
            Simulation.END_SETUP:       [],
            Simulation.START_RUN:       [],
            Simulation.END_RUN:         [],
        }

        self._meta_mutex: Lock                  = Lock()
        self._meta_cancelled: bool              = False
        self._meta_failed: bool                 = False
        self._meta_error_details: List[str]     = []

        self._meta_create_time                  = datetime.now()
        self._meta_start_time                   = None
        self._meta_end_time                     = None

        self._project_info_set: bool            = False
        self._project_sim_id: UUID              = None
        self._project_sim_base_path: str             = None

    @property
    def sim_path(self) -> Union[str, None]:
        if self._project_info_set:
            return os.path.join(self._project_sim_base_path, str(self._project_sim_id))
        else:
            return None

    def set_project_info(self, project_sim_base_path: str, sim_id: UUID):
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
    
    def set_cancelled(self) -> None:
        with self._meta_mutex:
            self._meta_cancelled = True
    def add_error_details(self, new_error: str) -> None:
        with self._meta_mutex:
            self._meta_error_details.append(new_error)

    def create_kwarg_defaults(self) -> Dict[str, Any]:
        return {}

    @property
    def name(self) -> str:
        return self.config.name
    @property
    def is_done(self) -> bool:
        return not self.thread.is_alive()

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
        new_kwargs = {}
        for k, v in old_kwargs.items():
            new_kwargs[k] = v
        for kwarg_dict in args:
            for key, value in kwarg_dict.items():
                new_kwargs[key] = value
        return new_kwargs
    def _check_kwargs_required(self, req_args: List[str], method_name, **kwargs):
        for arg in req_args:
            if arg not in kwargs:
                logger.error(f"Argument '{arg}' not provided for method '{method_name}' of {type(self)}")
                raise ValueError(f"Argument '{arg}' not provided for method '{method_name}' of {type(self)}")
    def _check_kwargs_optional(self, req_args: List[str], method_name, **kwargs):
        for arg in req_args:
            if arg not in kwargs:
                logger.warning(f"Argument '{arg}' not provided for method '{method_name}' of {type(self)}")

    def start(self, **kwargs):
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
        channel_values["error_details"] = self._meta_error_details
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


    @abstractmethod
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

    @abstractmethod
    def run(self, **kwargs) -> None:
        logger.debug(f"Simulation run() kwargs: {kwargs}.")
        # Start run callbacks
        try:
            self.trigger_callbacks(Simulation.START_RUN)
        except Exception:
            logger.exception(f"Exception when running Simulation '{Simulation.START_SETUP}' callbacks.")
        # Run
        try:
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