import cv2
import asyncio
import base64
import concurrent.futures
import multiprocessing
from skimage.metrics import structural_similarity as ssim

face_cascade = cv2.CascadeClassifier('./haarcascades/haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier('./haarcascades/haarcascade_eye.xml')
pool = concurrent.futures.ThreadPoolExecutor(max_workers=5)

def get_similarity(f1, f2):
    result = multiprocessing.Value('d', 0.0)
    p = multiprocessing.Process(target=run_get_similarity, args=(f1,f2,result))
    p.start()
    p.join()
    return result.value

def run_get_similarity(f1, f2, result):
    f1_gray = cv2.cvtColor(f1, cv2.COLOR_BGR2GRAY)
    f2_gray = cv2.cvtColor(f2, cv2.COLOR_BGR2GRAY)
    f2_resized = cv2.resize(f2_gray, f1.shape[:2], interpolation = cv2.INTER_AREA)
    result.value = ssim(f1_gray, f2_resized)

def extract_face(img):
    q = multiprocessing.Queue()
    p = multiprocessing.Process(target=run_extract_face, args=(img, q))
    p.start()
    p.join()
    faces = []
    while q.empty() is False:
        faces.append(q.get())
    return faces

def run_extract_face(img, q):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    for (x, y, w, h) in faces:
        face_only = gray[y:y+h,x:x+w]
        eyes = eye_cascade.detectMultiScale(face_only)
        if len(eyes) > 0:
            q.put((x, y, w, h))

def get_all_faces(frame):
    faces = extract_face(frame)
    cropped = []
    for face in faces:
        x, y, w, h = face
        face_only = frame[y:y+h,x:x+w,:]
        cropped.append(face_only)
    return cropped

async def detect_faces(frames_queue, events_queue):
    print("Detecting frames")
    TRESHOLD = 0.5
    count=0
    unique_faces = []
    while True:
        frame, isFinal = await frames_queue.get()
        if (count % 10 == 0):
            print(f"Received {count}")
        count+=1
        if isFinal == True:
            print("Final frame been processed")
            events_queue.put_nowait({"last": True})
            break;
        try:
            faces = get_all_faces(frame)
        except:
            faces=[]
            print("get_all_faces exception")
        for face in faces:
            is_unique = True
            for existing_face in unique_faces[-10:]:
                sim_score = get_similarity(existing_face, face)
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
