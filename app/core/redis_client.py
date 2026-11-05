import redis.asyncio as redis

from app.core.config import settings

# FastAPI에서 쓰는 Redis 비동기 클라이언트 (과제 1-1)
# - 예측 작업을 큐에 넣고(LPUSH), 결과 채널을 구독(SUBSCRIBE)할 때 사용
# - 큐·채널 이름은 worker/task_contract.py의 약속을 그대로 사용
# - 비동기(async) 클라이언트라 await로 호출: await redis_client.lpush(...)


# ===== [김도엽] Redis 비동기 클라이언트 연결 =====
# TODO: settings.REDIS_HOST, settings.REDIS_PORT로 클라이언트 만들기
#       decode_responses=True를 주면 bytes 대신 문자열로 받음
redis_client: redis.Redis = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    decode_responses=True,
)