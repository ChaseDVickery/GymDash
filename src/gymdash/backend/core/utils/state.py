from typing import Union, Any

STATE_NONE = "<<none>>"

class SimpleStateStack:
    def __init__(self):
        self.state_stack: list[Union[str,Any]] = [STATE_NONE]

    def reset_state(self):
        self.state_stack.clear()
        self.state_stack.append(STATE_NONE)
    @property
    def state(self):
        return self.state_stack[-1]
    @property
    def full_state(self):
        return "/".join(self.state_stack[1:])
    def push_state(self, state):
        self.state_stack.append(state)
    def pop_state(self):
        # Cannot pop the final "empty" state
        if (self.state == STATE_NONE):
            return
        self.state_stack.pop()