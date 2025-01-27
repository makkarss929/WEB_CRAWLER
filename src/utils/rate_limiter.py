import time
import asyncio
from collections import defaultdict


class DomainRateLimiter:
    def __init__(self, base_delay=1.0):
        self.domain_timers = defaultdict(float)
        self.base_delay = base_delay

    async def throttle(self, domain):
        now = time.time()
        last_request = self.domain_timers[domain]

        if now - last_request < self.base_delay:
            delay = self.base_delay - (now - last_request)
            await asyncio.sleep(delay)

        self.domain_timers[domain] = time.time()