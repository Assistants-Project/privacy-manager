import asyncio
import json
import logging
import websockets
from settings import DHT_HOST, DHT_PORT

log = logging.getLogger("WebSocketClient")

class WSClient:
    def __init__(self, message_queue):
        self._host = DHT_HOST
        self._port = DHT_PORT
        self._ws = None
        self._message_queue = message_queue

    async def run(self):
        backoff = 1
        while True:
            try:
                async with websockets.connect(f"ws://{self._host}:{self._port}/ws") as self._ws:
                    log.info("Connected to Smartotum DHT WebSocket")
                    backoff = 1
                    async for message in self._ws:
                        data = json.loads(message)
                        await self._message_queue.put(data)
            except asyncio.CancelledError:
                log.debug("WebSocket listener cancelled")
                raise
            except Exception as e:
                log.debug(f"WebSocket connection error: {e}. Retrying in {backoff}s...")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)
