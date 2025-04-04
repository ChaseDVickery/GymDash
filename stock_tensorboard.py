from src.tests.stock.train import train
from tensorboard.backend.event_processing import event_accumulator, tag_types, event_multiplexer
import os

if __name__ == "__main__":
    mult = event_multiplexer.EventMultiplexer(
        {"test_name": os.path.join("tb", "stock", "train", "PPO_1")}
    )
    mult.Reload()
    acc = mult.GetAccumulator("test_name")


    # acc = event_accumulator.EventAccumulator(
    #     # "asdfasdfasdfafdff"
    #     # os.path.join("tb", "stock", "train")
    #     os.path.join("tb", "stock", "train", "PPO_1")
    #     # r"D:\GymDash\GymDash\tb\stock\train\PPO_1\events.out.tfevents.1743731739.DESKTOP-BG5BDK1.13796.0"
    #     # "D:\\GymDash\\GymDash\\tb\\stock\\train\\PPO_1"
    #     # os.path.join("tb", "stock", "train", "PPO_1", "events.out.tfevents.1743730750.DESKTOP-BG5BDK1.13396.0")
    # )
    # acc.Reload()

    print(acc.scalars.Keys())
    print(acc.tensors.Keys())
    scalars = acc.Tags()[tag_types.SCALARS]
    print(acc.Tags())
    print(scalars)