class TTLCache:
    def __init__(self, clock):
        self.clock = clock
        # storage: key -> (value, expires_at)
        self._store = {}

    def set(self, key, value, ttl):
        if not isinstance(ttl, (int, float)) or isinstance(ttl, bool) or ttl <= 0:
            raise ValueError("ttl must be a strictly positive number")
        now = self.clock()
        self._store[key] = (value, now + ttl)

    def get(self, key):
        if key not in self._store:
            raise KeyError(key)
        val, expires_at = self._store[key]
        now = self.clock()
        if now >= expires_at:
            del self._store[key]
            raise KeyError(key)
        return val

    def delete(self, key):
        if key in self._store:
            del self._store[key]
            return True
        return False
