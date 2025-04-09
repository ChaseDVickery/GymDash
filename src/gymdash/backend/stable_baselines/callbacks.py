from stable_baselines3.common.callbacks import BaseCallback
from src.gymdash.backend.core.simulation import SimulationInteractor
from src.gymdash.backend.gymnasium.utils.wrapper_utils import WrapperUtils
from src.gymdash.backend.gymnasium.wrappers import TensorboardStreamWrapper

class TensorboardPathCorrectionCallback(BaseCallback):
    def __init__(self, verbose: int = 0):
        super().__init__(verbose)

    def _on_step(self) -> bool:
        return super()._on_step()

    def _on_training_start(self) -> None:
        """
        This method is called before the first rollout starts.
        """
        if (self.model):
            tb_log_wrapper: TensorboardStreamWrapper = WrapperUtils.get_wrapper_of_type(self.model.env, TensorboardStreamWrapper)
            if tb_log_wrapper:
                print(f"Setting wrapper log path to '{self.model.logger.get_dir()}'")
                tb_log_wrapper.set_log_path(self.model.logger.get_dir())


class SimulationInteractionCallback(BaseCallback):
    def __init__(self, simulation_interactor: SimulationInteractor, verbose: int = 0):
        super().__init__(verbose)
        self.interactor = simulation_interactor
        
        self.curr_timesteps = 0
        self.total_timesteps = 0

    # def consume_interactors(self) -> None:
    #     self.interactor.consume_triggers()

    def _on_training_start(self) -> None:
        # From the ProgressBarCallback
        self.total_timesteps = self.locals["total_timesteps"] - self.model.num_timesteps

    def _on_rollout_start(self) -> None:
        pass

    def _on_step(self) -> bool:
        # HANDLE OUTGOING INFORMATION
        # Return progress value equivalent to the one used in ProgressBarCallback
        self.curr_timesteps += self.training_env.num_envs
        self.interactor.set_out_if_in("progress", (self.curr_timesteps, self.total_timesteps))
        # HANDLE INCOMING INFORMATION
        if self.interactor.get_in("stop_simulation")[0]:
            return False
        return True

    def _on_rollout_end(self) -> None:
        pass

    def _on_training_end(self) -> None:
        pass