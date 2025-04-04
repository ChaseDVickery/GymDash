from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from random import randint
import numpy as np

import traceback

from threading import Thread
from src.tests.stock.train import train

from src.api.internals.logging.streamables.StreamerRegistry import StreamerRegistry

from .internals.usage import get_usage_simple, get_usage_detailed, get_usage_gpu


# Setup our API
app = FastAPI(title="GymDash", description="API for interacting with active simulation environments", version="0.0.1")

# Setup CORS middleware so that our API will accept
# communication from our frontend
origins = [
    # "*"
]
regex_origins = r"^((.*127.0.0.1.*)|(.*localhost.*))$"
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=regex_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup gzip compression middleware
# https://fastapi.tiangolo.com/advanced/middleware/#trustedhostmiddleware
app.add_middleware(
    GZipMiddleware,
    # Messages below minimum_size (in bytes) will not be compressed
    minimum_size=1_000_000,
    # Compression level 1-9 (1 lowest compression, 9 highest compression)
    compresslevel=1
)

def start_test_simulation():
    train()
def setup_backend():
    sim_listener_thread = Thread(target=start_test_simulation)
    sim_listener_thread.start()

setup_backend()

@app.get("/")
async def test():
    return {
        "Message": "This is the result of an API call."
    }

@app.get("/random")
async def thinking_of_a_number():
    return {
        "value": randint(1, 10)
    }

@app.get("/big-data1000")
async def thinking_of_a_number2():
    return {
        "value": np.random.random((10, 10, 10)).flatten().tolist()
    }

@app.get("/big-data100000")
async def thinking_of_a_number3():
    return {
        "value": np.random.random(100_000).flatten().tolist()
    }

# https://stackoverflow.com/questions/73921756/how-to-add-gzip-middleware-for-the-fastapi
@app.get("/big-data1000000")
async def thinking_of_a_number4():
    return {
        "value": np.random.random((100, 100, 100)).flatten().tolist()
    }

@app.get("/resource-usage-simple")
async def get_resource_usage_simple():
    return get_usage_simple()

@app.get("/resource-usage-detailed")
async def get_resource_usage_detailed():
    return get_usage_detailed()

@app.get("/resource-usage-gpu")
async def get_resource_usage_gpu():
    return get_usage_gpu()


@app.get("/read-key/")
async def get_read_test(exp_key: str, key: str, recent: bool = True):
    """
    Parameters:
        exp_key:    The experiment key. Points towards the
            internal tb file containing the stats.
        key:        The scalar stat key to query.
        recent:     If true, only queries and returns the
            most recently acquired values from the key.
            If false, returns the entire data sequence.
    """
    streamer = StreamerRegistry.get_streamer(exp_key)
    print(streamer)
    if not streamer:
        return {}
    else:
        try:
            recent = streamer.get_all_recent()
            print(recent)
            return recent
        except Exception as e:
            print(f"caught exception: {e}")
            traceback.print_exc()
        return {}