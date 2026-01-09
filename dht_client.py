import aiohttp
import logging
from settings import DHT_HOST, DHT_PORT

log = logging.getLogger("DHTClient")

BASE_URL = f"http://{DHT_HOST}:{DHT_PORT}"

async def fetch_all_topics():
    url = f"{BASE_URL}/get_all"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            log.debug(f"GET {url}: status {resp.status}")
            return await resp.json()

async def fetch_topics(name):
    url = f"{BASE_URL}/topic_name/{name}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            log.debug(f"GET {url}: status {resp.status}")
            return await resp.json()

async def fetch_topic(name, uuid):
    url = f"{BASE_URL}/topic_name/{name}/topic_uuid/{uuid}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            log.debug(f"GET {url}: status {resp.status}")
            return await resp.json()

async def update_topic(name, uuid, payload):
    url = f"{BASE_URL}/topic_name/{name}/topic_uuid/{uuid}"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            log.debug(f"POST {url}: updated topic {name}:{uuid} with payload {payload}")
            resp.raise_for_status()

async def delete_topic(name, uuid):
    url = f"{BASE_URL}/topic_name/{name}/topic_uuid/{uuid}"
    async with aiohttp.ClientSession() as session:
        async with session.delete(url) as resp:
            log.debug(f"DELETE {url}: status {resp.status}")
            resp.raise_for_status()
