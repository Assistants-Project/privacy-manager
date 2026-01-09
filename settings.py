"""Handle configuration of environment variables"""

import os

DHT_HOST = os.getenv("DHT_HOST", "localhost")
DHT_PORT = int(os.getenv("DHT_PORT", 3000))
