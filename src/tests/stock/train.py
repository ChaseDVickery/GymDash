# Example training script taken from a post by Zhi Li:
# https://medium.com/datapebbles/building-a-trading-bot-with-deep-reinforcement-learning-drl-b9519a8ba2ac

from .StockTradingEnv import StockTradingEnv
from pybroker import YFinance
import pybroker
pybroker.enable_data_source_cache('yfinance')
import pandas as pd
from stable_baselines3 import PPO

# from src.api.internals.callbacks import LogTrainingInfo
# from src.simulation.logging.callbacks import LogTrainingInfoCallback
from src.simulation.logging.callbacks import LogTrainingInfoCallback
from src.simulation.logging.wrappers import LogTrainingInfoWrapper

def train():
    yfinance = YFinance()
    df = yfinance.query(['AAPL'], start_date='3/1/2021', end_date='3/1/2022')
    df['date'] = pd.to_datetime(df['date']).dt.date
    env = StockTradingEnv(df, initial_balance=100000, commission_fee=0.0001, slippage_cost=0.005)
    env = LogTrainingInfoWrapper(env, "testout")

    # logging_callback = LogTrainingInfoCallback("")

    model = PPO("MlpPolicy", env, verbose=0)
    # model.learn(total_timesteps=1_000, progress_bar=True, callback=logging_callback)
    model.learn(total_timesteps=1_000, progress_bar=True)
    model.save("ppo_aapl")


    print(env.episode_logs)

if __name__ == "__main__":
    train()