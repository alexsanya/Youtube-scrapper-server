from fastapi import FastAPI, WebSocket
import logging
from modules.pipeline import processing_pipeline

app = FastAPI()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)

@app.websocket("/process")
async def processing_endpoint(websocket: WebSocket, video: str):
    await websocket.accept()
    await processing_pipeline(websocket, video)
    logger.debug(f"New client connected. Url: {video}")
