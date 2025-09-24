import time
from collections import defaultdict, deque

_last_sent = defaultdict(float)   # cluster_id -> ts

def should_send(cluster_id:str, cooldown:int=600)->bool:
    now=time.time()
    if now - _last_sent[cluster_id] >= cooldown:
        _last_sent[cluster_id]=now
        return True
    return False
