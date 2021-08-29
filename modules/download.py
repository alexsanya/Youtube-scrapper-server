import os
import pytube
import hashlib
import asyncio
import logging
import concurrent.futures

DOWNLOAD_PATH = './video'

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)

async def download_video(video_url, events_queue):
    loop = asyncio.get_event_loop()
    events_queue.put_nowait({"step": "Downloading video"})
    with concurrent.futures.ThreadPoolExecutor() as pool:
        filename, full_path = await loop.run_in_executor(pool, run_download_video, video_url)
    return (filename, full_path)

def run_download_video(video_url):
    logger.debug("Downloading video...")
    if not os.path.exists(DOWNLOAD_PATH):
        os.mkdir(DOWNLOAD_PATH)
    video = pytube.YouTube(video_url)
    stream = video.streams.get_by_resolution('360p')
    filename = hashlib.md5(video_url.encode()).hexdigest()
    stream.download(DOWNLOAD_PATH, filename=filename)
    return (filename,  f"{DOWNLOAD_PATH}/{filename}")

