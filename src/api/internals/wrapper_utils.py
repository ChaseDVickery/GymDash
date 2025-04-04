from typing import Type
import gymnasium as gym
from stable_baselines3.common.vec_env import (
    DummyVecEnv,
    VecEnv,
    VecNormalize,
    VecTransposeImage,
    is_vecenv_wrapped,
    unwrap_vec_normalize,
)

class WrapperUtils:
    def get_wrapper_of_type(env:gym.Env, wrapper_type:Type):
        curr:gym.Env = env
        if (isinstance(curr, DummyVecEnv)):
            next:gym.Env = curr.get_attr("env", [0])[0]
            print(f"here {next}")
        else:
            next:gym.Env = curr.env
            print(f"there {next}")
        while curr != next:
            if isinstance(curr, wrapper_type):
                return curr
            else:
                curr = next
                if (isinstance(curr, DummyVecEnv)):
                    print(f"here {curr.get_attr('env', [0])[0]}")
                    next:gym.Env = curr.get_attr("env", [0])[0]
                else:
                    print(f"there {curr.env}")
                    next:gym.Env = curr.env
        return None