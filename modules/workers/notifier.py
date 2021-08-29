import time

async def notify_client(events_queue, websocket):
    while True:
        event = await events_queue.get()
        event["time"] = time.time()
        await websocket.send_json(event)
        if "last" in event:
            break
