from uuid import uuid4 # позволяет генерировать уникальные id

from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI()


@app.get("/")
async def welcome() -> dict:
    return {"message": "Hello, FastAPI!"}