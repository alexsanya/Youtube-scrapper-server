import cv2
import asyncio
import base64
import concurrent.futures
from skimage.metrics import structural_similarity as ssim

face_cascade = cv2.CascadeClassifier('./haarcascades/haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier('./haarcascades/haarcascade_eye.xml')

async def get_similarity(f1, f2):
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        score = await loop.run_in_executor(pool, run_get_similarity, f1, f2)
        return score

def run_get_similarity(f1, f2):
    f1_gray = cv2.cvtColor(f1, cv2.COLOR_BGR2GRAY)
    f2_gray = cv2.cvtColor(f2, cv2.COLOR_BGR2GRAY)
    f2_resized = cv2.resize(f2_gray, f1.shape[:2], interpolation = cv2.INTER_AREA)
    return ssim(f1_gray, f2_resized)

async def extract_face(img):
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        img, proper_faces = await loop.run_in_executor(pool, run_extract_face, img)
        return (img, proper_faces)

def run_extract_face(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    proper_faces = []
    for (x, y, w, h) in faces:
        face_only = gray[y:y+h,x:x+w]
        eyes = eye_cascade.detectMultiScale(face_only)
        if len(eyes) > 0:
            proper_faces.append((x, y, w, h))
    return (img, proper_faces)

async def get_all_faces(frame):
    img, faces = await extract_face(frame)
    cropped = []
    for face in faces:
        x, y, w, h = face
        face_only = img[y:y+h,x:x+w,:]
        cropped.append(face_only)
    return cropped

async def detect_faces(frames_total, frames_queue, events_queue):
    TRESHOLD = 0.5
    count=0
    unique_faces = []
    while True:
        frame, isFinal = await frames_queue.get()
        if (count % 10 == 0):
            events_queue.put_nowait({"progress": count*5 / frames_total})
            print(f"Received {count}")
        count+=1
        if isFinal == True:
            print("Final frame been processed")
            events_queue.put_nowait({"last": True})
            break;
        try:
            faces = await get_all_faces(frame)
        except:
            faces=[]
            print("get_all_faces exception")
        for face in faces:
            is_unique = True
            for existing_face in unique_faces[-10:]:
                sim_score = await get_similarity(existing_face, face)
                if sim_score > TRESHOLD:
                    is_unique = False
            if is_unique:
                unique_faces.append(face)
                _, buffer = cv2.imencode('.jpg', face)
                serialized_picture = base64.b64encode(buffer)
                events_queue.put_nowait({
                    "step": "New face been detected",
                    "picture": serialized_picture.decode(),
                })

        frames_queue.task_done()
