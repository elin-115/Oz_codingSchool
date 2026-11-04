import os

import redis

# AI 워커에서 쓰는 Redis 동기 클라이언트 (과제 2-1)
# - 큐에서 작업을 꺼내고(BRPOP), 결과를 보낼 때(PUBLISH) 사용
# - 워커는 FastAPI 설정(app/core/config.py)을 쓰지 않으므로 환경 변수를 직접 읽음
#   (도커에서는 compose가 REDIS_HOST=redis로 넣어 줌)

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))


# ===== [박유정] Redis 동기 클라이언트 연결 =====
# TODO: REDIS_HOST, REDIS_PORT로 동기 클라이언트 만들기 (decode_responses=True 권장)
redis_client: redis.Redis = ...
