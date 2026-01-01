from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable, Optional, Union
from gymdash.backend.core.utils.state import SimpleStateStack

if TYPE_CHECKING:
    from stable_baselines3.common import base_class
try:
    import torch.nn as nn
    _has_torch = True
except ImportError:
    _has_torch = False

from contextlib import contextmanager


class BaseCustomCallback(ABC):
    """
    Base class for custom callback. Takes most logic from
    stable baseline's BaseCallback.
    """

    NO_STATE = "<<none>>"

    def __init__(self):
        if not _has_torch:
            raise ImportError(f"Install pytorch to use {type(self)}.")
        super().__init__()
        # Number of time the callback was called
        self.n_calls = 0  # type: int
        self.locals: dict[str, Any] = {}
        self.globals: dict[str, Any] = {}
        self.sm: SimpleStateStack = SimpleStateStack()
        # Sometimes, for event callback, it is useful
        # to have access to the parent object
        self.parent = None  # type: Optional[BaseCustomCallback]

    @contextmanager
    def context(self, *temp_states):
        for temp_state in temp_states:
            self.push_state(temp_state)
        yield
        for _ in temp_states:
            self.pop_state()

    # Type hint as string to avoid circular import
    def init_callback(self) -> None:
        self.reset_state()
        self._init_callback()

    def _init_callback(self) -> None:
        pass

    def reset_state(self):
        self.sm.reset_state()
    @property
    def state(self):
        return self.sm.state
    @property
    def full_state(self):
        return self.sm.full_state
    def push_state(self, state):
        self.sm.push_state(state)
    def pop_state(self):
        self.sm.pop_state()

    def on_process_start(self, locals_: dict[str, Any], globals_: dict[str, Any]) -> None:
        # Those are reference and will be updated automatically
        self.locals = locals_
        self.globals = globals_
        self._on_process_start()

    def _on_process_start(self) -> None:
        pass

    @abstractmethod
    def _on_invoke(self):
        pass
    def on_invoke(self, temp_state=None):
        self.n_calls += 1
        if temp_state is not None:
            self.push_state(temp_state)
        success = self._on_invoke()
        if temp_state is not None:
            self.pop_state()
        return success
        

    # From stable baselines
    def update_locals(self, locals_: dict[str, Any]) -> None:
        """
        Update the references to the local variables.

        :param locals_: the local variables during rollout collection
        """
        self.locals.update(locals_)
        self.update_child_locals(locals_)
    # From stable baselines
    def update_child_locals(self, locals_: dict[str, Any]) -> None:
        """
        Update the references to the local variables on sub callbacks.

        :param locals_: the local variables during rollout collection
        """
        pass

class CallbackCustomList(BaseCustomCallback):
    """
    Class for chaining callbacks.

    :param callbacks: A list of callbacks that will be called
        sequentially.
    """

    def __init__(self, callbacks: list[BaseCustomCallback]):
        super().__init__()
        assert isinstance(callbacks, list)
        self.callbacks = callbacks

    def _init_callback(self) -> None:
        for callback in self.callbacks:
            callback.init_callback()
            callback.parent = self.parent

    def _on_process_start(self) -> None:
        for callback in self.callbacks:
            callback.on_process_start(self.locals, self.globals)

    def _on_invoke(self):
        continue_process = True
        for callback in self.callbacks:
            continue_process &= callback.on_invoke()
        return continue_process

    def update_child_locals(self, locals_: dict[str, Any]) -> None:
        """
        Update the references to the local variables.

        :param locals_: the local variables during rollout collection
        """
        for callback in self.callbacks:
            callback.update_locals(locals_)

    def reset_state(self):
        super().reset_state()
        for callback in self.callbacks:
            callback.reset_state()
    def push_state(self, state):
        super().push_state(state)
        for callback in self.callbacks:
            callback.push_state(state)
    def pop_state(self):
        super().pop_state()
        for callback in self.callbacks:
            callback.pop_state()

class EmptyCallback(BaseCustomCallback):
    def __init__(self):
        super().__init__()
    def _on_invoke(self):
        return True