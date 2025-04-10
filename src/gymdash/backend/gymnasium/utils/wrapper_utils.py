from typing import Type

try:
    import gymnasium as gym
    _has_gym = True
except ImportError:
    _has_gym = False
    
try:
    from stable_baselines3.common.vec_env import (DummyVecEnv, VecEnv,
                                                  VecNormalize,
                                                  VecTransposeImage,
                                                  is_vecenv_wrapped,
                                                  unwrap_vec_normalize)
    _has_sb = True
except ImportError:
    _has_sb = False
    

class WrapperUtils:
    def _get_next_wrapper(env:gym.Env) -> gym.Env:
        if _has_sb:
            if isinstance(env, DummyVecEnv):
                next:gym.Env = env.get_attr("env", [0])[0]
            else:
                next:gym.Env = env.env
        else:
            next:gym.Env = env.env
        return next

    def get_wrapper_of_type(env:gym.Env, wrapper_type:Type) -> gym.Env:
        if not _has_gym:
            raise ImportError(f"Cannot get environment wrapper type without gymnasium. Consider installing gymnasium.")
        curr:gym.Env = env
        next = WrapperUtils._get_next_wrapper(env)
        while curr != next:
            if isinstance(curr, wrapper_type):
                return curr
            else:
                curr = next
                next = WrapperUtils._get_next_wrapper(curr)
        return None