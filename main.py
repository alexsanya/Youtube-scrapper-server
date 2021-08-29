from fastapi import FastAPI, WebSocket
import logging
import pytube
from modules.processing import processing_pipeline
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/video-info/")
def get_video_info(video_url: str):
    video = pytube.YouTube(video_url)
    return {
        "title": video.title,
        "preview": video.thumbnail_url
    }

@app.websocket("/process")
async def processing_endpoint(websocket: WebSocket, video: str):
    await websocket.accept()
    logger.debug(f"New client connected. Url: {video}")
    await processing_pipeline(websocket, video)
