import logging
from typing import List
import threading
import asyncio
import concurrent.futures
from fastapi import WebSocket
from .pipeline import processing_pipeline
import queue

MAX_WORKERS=3

logger = logging.getLogger('Pool')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)

class Pool:
    def __init__(self):
        #self.clients = []
        #self.pool_executor = concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS)

    async def connect(self, websocket: WebSocket, video_url: str):
            await websocket.accept()
            logger.debug(f"Starting new thread. Threads total: {len(self.clients)}")
            await processing_pipeline(websocket, video_url)

    #def disconnect(self, websocket: WebSocket):
        #filtered_clients = []
        #for client in self.clients:
        #    if client["socket"] == websocket:
        #        client["future"].cancel()
        #    else:
        #        filtered_clients.append(client)
        #self.clients = filtered_clients


