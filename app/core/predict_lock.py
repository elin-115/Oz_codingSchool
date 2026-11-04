from app.core.redis_client import redis_client
from worker.task_contract import MODEL_NAME, RESULT_TIMEOUT

# 따닥 방지 락 (동시 요청 문제 해결)
# 같은 진료기록 예측을 동시에 여러 번 요청하면 첫 번째만 진행하고 나머지는 막음
# Redis SET NX: 키가 "없을 때만" 저장 → 동시에 와도 딱 하나만 성공 (Redis 명령은 원자적)

# 락이 자동으로 풀리는 시간(초). 결과 대기 시간보다 조금 길게
# 서버가 죽어서 release를 못 해도 이 시간이 지나면 저절로 풀림
LOCK_EXPIRE = RESULT_TIMEOUT + 10


def _lock_key(record_id: int) -> str:
    # 진료기록 + 모델마다 락 하나. 예: "ai:predict:lock:12:ensemble_3models_fold1_v1"
    return f"ai:predict:lock:{record_id}:{MODEL_NAME}"


async def acquire_predict_lock(record_id: int) -> bool:
    # 락 잡기. 성공하면 True, 이미 누가 예측 중이면 False
    ok = await redis_client.set(_lock_key(record_id), "1", nx=True, ex=LOCK_EXPIRE)
    return bool(ok)


async def release_predict_lock(record_id: int) -> None:
    # 락 풀기 (예측이 끝나면 꼭 호출)
    await redis_client.delete(_lock_key(record_id))