# Example training script taken from a post by Zhi Li:
# https://medium.com/datapebbles/building-a-trading-bot-with-deep-reinforcement-learning-drl-b9519a8ba2ac

from .StockTradingEnv import StockTradingEnv
from pybroker import YFinance
import pybroker
pybroker.enable_data_source_cache('yfinance')
import pandas as pd
from stable_baselines3 import PPO
import os

# from src.api.internals.callbacks import LogTrainingInfo
from src.api.internals.logging.callbacks import LogTrainingInfoCallback, TensorboardPathCorrectionCallback
from src.api.internals.logging.wrappers.LogTrainingInfoWrapper import LogTrainingInfoWrapper
from src.api.internals.logging.wrappers.TensorboardStreamWrapper import TensorboardStreamWrapper
from src.api.internals.wrapper_utils import WrapperUtils

def train():
    tb_path = os.path.join("tb", "stock", "train")
    yfinance = YFinance()
    df = yfinance.query(['AAPL'], start_date='3/1/2021', end_date='3/1/2022')
    df['date'] = pd.to_datetime(df['date']).dt.date
    env = StockTradingEnv(df, initial_balance=100000, commission_fee=0.0001, slippage_cost=0.005)
    env = LogTrainingInfoWrapper(env, "testout")
    env = TensorboardStreamWrapper(env, tb_path, ["rewards", "rollout/ep_rew_mean"])

    # logging_callback = LogTrainingInfoCallback("")
    tb_correction_callback = TensorboardPathCorrectionCallback()

    model = PPO("MlpPolicy", env, verbose=0, tensorboard_log=tb_path)
    # model.learn(total_timesteps=1_000, progress_bar=True, callback=logging_callback)
    model.learn(total_timesteps=10_000, progress_bar=True, callback=tb_correction_callback)
    model.save("ppo_aapl")


    print(WrapperUtils.get_wrapper_of_type(env, LogTrainingInfoWrapper).episode_logs)

if __name__ == "__main__":
    train()