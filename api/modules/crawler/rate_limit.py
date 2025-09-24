import time
from collections import defaultdict, deque

class DomainRateLimiter:
    def __init__(self, max_rps:float=0.8, max_concurrent:int=2):
        self.max_rps = max_rps
        self.max_conc = max_concurrent
        self.calls = defaultdict(deque)   # domain -> deque[timestamps]
        self.inflight = defaultdict(int)

    def acquire(self, domain:str):
        while True:
            now = time.time()
            dq = self.calls[domain]
            while dq and now - dq[0] > 1.0:
                dq.popleft()
            if len(dq) < max(1, int(self.max_rps)) and self.inflight[domain] < self.max_conc:
                dq.append(now)
                self.inflight[domain] += 1
                return
            time.sleep(0.05)

    def release(self, domain:str):
        self.inflight[domain] = max(0, self.inflight[domain]-1)
