import asyncio, time
from collections import defaultdict

class AlertBus:
    def __init__(self, cooldown_sec:int=600):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.last_sent = defaultdict(float)
        self.cooldown = cooldown_sec

    def should_send(self, cluster_id:str)->bool:
        now = time.time()
        if now - self.last_sent[cluster_id] >= self.cooldown:
            self.last_sent[cluster_id] = now
            return True
        return False

    async def publish(self, payload:dict):
        await self.queue.put(payload)

    async def stream(self):
        while True:
            item = await self.queue.get()
            yield item

# 글로벌 싱글톤
bus = AlertBus(cooldown_sec=600)
