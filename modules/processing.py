import asyncio
import logging
from fastapi import WebSocket, WebSocketDisconnect
from modules.download import download_video
from modules.workers.split import split_to_frames
from modules.workers.notifier import notify_client
from modules.workers.face_detector import detect_faces

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)

async def processing_pipeline(websocket: WebSocket, video_url: str):
    events_queue = asyncio.Queue()
    frames_queue = asyncio.Queue(maxsize = 500)
    filename, fullname = await download_video(video_url, events_queue)
    logger.debug(f"Uploaded {filename}")
    logger.debug(fullname)
    frames_split_worker = asyncio.create_task(split_to_frames(fullname, frames_queue))
    face_detection_worker = asyncio.create_task(detect_faces(frames_queue, events_queue))
    notifications_worker = asyncio.create_task(notify_client(events_queue, websocket))
    tasks = [frames_split_worker, face_detection_worker, notifications_worker]
    await asyncio.gather(*tasks, return_exceptions=True)
    logger.debug("All tasks been finished")
