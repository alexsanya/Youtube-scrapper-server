import logging
from fastapi import WebSocket
import asyncio
import hashlib
import os
import pytube
import cv2
import time
import base64
from skimage.metrics import structural_similarity as ssim
import concurrent.futures

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)

DOWNLOAD_PATH = './video'

face_cascade = cv2.CascadeClassifier('./haarcascades/haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier('./haarcascades/haarcascade_eye.xml')

def get_video_info(video_url: str):
    video = pytube.YouTube(video_url)
    return {
        "title": video.title,
        "preview": video.thumbnail_url
    }

def download_video(*args):
    video_url, *_ = args
    if not os.path.exists(DOWNLOAD_PATH):
        os.mkdir(DOWNLOAD_PATH)
    video = pytube.YouTube(video_url)
    stream = video.streams
    stream = video.streams.get_by_resolution('360p')
    filename = hashlib.md5(video_url.encode()).hexdigest()
    stream.download(DOWNLOAD_PATH, filename=filename)
    return (filename,  f"{DOWNLOAD_PATH}/{filename}")

def video_to_frames(*args):
    filename, fullpath, *_ = args
    frames_dir = f'./frames_{filename}'
    if not os.path.exists(frames_dir):
        os.mkdir(frames_dir)
    time_start = time.time()
    cap = cv2.VideoCapture(fullpath)
    video_length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    logger.debug(f"Number of frames: {video_length}")
    count = 0
    logger.debug("Converting video..")
    while cap.isOpened():
        ret,frame = cap.read()
        if ret == False:
            break
        count = count + 1
        if not count % 5 ==0:
            continue
        cv2.imwrite(frames_dir + '/' + f"frame{count}.jpg", frame)

        if (count % 10 == 0):
            print(f"Processes {count}/{video_length}")
    time_end = time.time()
    cap.release()
    logger.debug(f"Done extracting frames.\n{count} frames extracted")
    logger.debug(f"It took {time_end-time_start} seconds for conversion.")
    return (filename, frames_dir)

def extract_face(frame):
    img = cv2.imread(frame)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    proper_faces = []
    for (x, y, w, h) in faces:
        face_only = gray[y:y+h,x:x+w]
        eyes = eye_cascade.detectMultiScale(face_only)
        if len(eyes) > 0:
            proper_faces.append((x, y, w, h))
    return (img, proper_faces)

def show_all_faces(frame):
    img, faces = extract_face(frame)
    cropped = []
    for face in faces:
        x, y, w, h = face
        face_only = img[y:y+h,x:x+w,:]
        cropped.append(face_only)
    return cropped

def get_similarity(p1, p2):
    p1_gray = cv2.cvtColor(p1, cv2.COLOR_BGR2GRAY)
    p2_gray = cv2.cvtColor(p2, cv2.COLOR_BGR2GRAY)
    p2_resized = cv2.resize(p2_gray, p1.shape[:2], interpolation = cv2.INTER_AREA)
    return ssim(p1_gray, p2_resized)

def process_frames(frames_dir, frames_total, frames, unique_faces):
    TRESHOLD = 0.5
    for fn, frame in enumerate(frames):
        faces = show_all_faces(f'{frames_dir}/'+frame)
        if fn % 10 == 0:
            logger.debug(f"Processing {fn}/{frames_total}")
        for face in faces:
            is_unique = True
            for existing_face in unique_faces[-10:]:
                if get_similarity(existing_face, face) > TRESHOLD:
                    is_unique = False
            if is_unique:
                logger.debug("Found new face")
                return (face, frames[fn:])
    return (None, [])

stages = [{
    "name": "Downloading video",
    "action": download_video
},
{
    "name": "Splitting into frames",
    "action": video_to_frames
}]

async def processing_pipeline(websocket: WebSocket, video_url: str):
    loop = asyncio.get_running_loop()

    logger.debug(f"New pipeline has started. Url: {video_url}")

    params = (video_url,)
    for stage in stages:
        await websocket.send_json({"step": stage["name"], "time": time.time()})
        with concurrent.futures.ThreadPoolExecutor() as pool:
            params = await loop.run_in_executor(pool, stage["action"], *params)

    filename, frames_dir = params
    artifacts_dir = f"./artifacts_{filename}"
    if not os.path.exists(artifacts_dir):
        os.mkdir(artifacts_dir)

    all_frames = os.listdir(f'{frames_dir}/')

    unique_faces = []
    frames_to_process = all_frames
    while (len(frames_to_process) > 0):
        with concurrent.futures.ThreadPoolExecutor() as pool:
            face, frames_to_process = await loop.run_in_executor(pool, process_frames, frames_dir, len(all_frames), frames_to_process, unique_faces)
            try:
                retval, buffer = cv2.imencode('.jpg', face)
                serialized_picture = base64.b64encode(buffer)
                await websocket.send_json({
                    "step": "New face been detected",
                    "picture": serialized_picture.decode(),
                    "time": time.time()
                })
                unique_faces.append(face)
                cv2.imwrite(f'{artifacts_dir}/{len(unique_faces)}.jpg', face)
            except:
                pass
    await websocket.send_json({
        "last": True
    })




