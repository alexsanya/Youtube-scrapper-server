import time
import cv2
import logging
import asyncio
import concurrent.futures


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)

async def split_to_frames(file, frames_queue, events_queue):
    loop = asyncio.get_running_loop()
    events_queue.put_nowait({"step": "Looking for faces"})
    with concurrent.futures.ThreadPoolExecutor() as pool:
        await loop.run_in_executor(pool, run, file, frames_queue, events_queue)

def run(file, frames_queue, events_queue):
    # Log start time
    time_start = time.time()

    cap = cv2.VideoCapture(file)
    video_length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    logging.debug(f"Number of frames: {video_length}")
    count = 0
    logging.debug("Converting video..")
    while cap.isOpened():
        ret,frame = cap.read()
        if ret == False:
            break
        count += 1
        if not count % 5 ==0:
            continue
        frames_queue.put_nowait([frame, False])
    time_end = time.time()
    cap.release()
    frames_queue.put_nowait([None, True]);
    logger.debug(f"Done extracting frames.\n{count} frames extracted")
    logger.debug(f"It took {time_end-time_start} seconds for conversion.")
