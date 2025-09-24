import json, logging, os, sys, time, uuid, contextvars
from pythonjsonlogger import jsonlogger

request_id_ctx = contextvars.ContextVar("request_id", default=None)

def get_request_id():
    rid = request_id_ctx.get()
    if rid:
        return rid
    rid = uuid.uuid4().hex[:12]
    request_id_ctx.set(rid)
    return rid

class JsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record.setdefault("level", record.levelname)
        log_record.setdefault("ts", int(time.time() * 1000))
        log_record.setdefault("logger", record.name)
        log_record.setdefault("rid", get_request_id())
        # 배포 환경 태그
        svc = os.getenv("SERVICE_NAME", "api")
        env = os.getenv("DEPLOY_ENV", "dev")
        log_record.setdefault("service", svc)
        log_record.setdefault("env", env)

def setup_logger(name: str = "app", level: str | int = None) -> logging.Logger:
    lvl = level or os.getenv("LOG_LEVEL", "INFO").upper()
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = JsonFormatter("%(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
    return logger

# 샘플 사용
log = setup_logger("app")
