# FastAPI와 AI 워커가 Redis로 주고받는 "약속"을 모아둔 파일
# ⚠️ torch 같은 무거운 라이브러리는 import하지 않음 (torch가 없는 FastAPI 이미지에서도 import해야 하니까)

# 작업 대기열 이름 (Redis List). FastAPI가 LPUSH, 워커가 BRPOP
QUEUE_NAME = "ai:predict:queue"

# 지금 서버에서 쓰는 AI 모델 이름 (worker/model.py에서 옮겨옴)
# 같은 진료기록 + 같은 모델이면 다시 예측하지 않고 DB에 있는 결과를 돌려줄 때 비교하는 값
MODEL_NAME = "ensemble_3models_fold1_v1"

# FastAPI가 결과를 기다리는 최대 시간(초). 넘으면 504
RESULT_TIMEOUT = 60


def result_channel(task_id: str) -> str:
    # 작업마다 자기 결과만 받도록 채널 이름에 task_id를 붙임
    # 예: "ai:predict:result:3f2a..."
    return f"ai:predict:result:{task_id}"