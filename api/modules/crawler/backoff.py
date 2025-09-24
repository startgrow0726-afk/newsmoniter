import random, time

def sleep_with_backoff(attempt:int, base:float=1.0, cap:float=300.0)->float:
    delay = min(cap, base * (2 ** attempt)) * (0.8 + 0.4*random.random())
    time.sleep(delay)
    return delay
