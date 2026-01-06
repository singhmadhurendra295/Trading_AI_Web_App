import time
from config import config

class SimpleCache:
    def __init__(self):
        self.cache = {}

    def get(self, key):
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < config.CACHE_TIMEOUT:
                return value
            else:
                del self.cache[key]
        return None

    def set(self, key, value):
        self.cache[key] = (value, time.time())

    def clear(self):
        self.cache.clear()

cache = SimpleCache()