from fastapi import FastAPI
from random import randint

app = FastAPI(title="GymDash", description="API for interacting with active simulation environments", version="0.0.1")

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