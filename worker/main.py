from worker.redis_client import redis_client
from worker.task_contract import MODEL_NAME, QUEUE_NAME, result_channel

# AI 워커 실행 파일 (과제 2-2). 실행: uv run python -m worker.main
# 큐에서 작업을 하나씩 꺼내 폐렴 예측 → 결과를 Publish
# 워커를 여러 개 띄워도 BRPOP은 작업 하나를 워커 하나에게만 줌 (다중 워커)
# 주고받는 JSON 형식은 docs/day10_AI워커_분리_설계.md 2장 참고


# ===== [박유정] 작업 하나 처리 =====
def handle_task(task: dict) -> dict:
    # TODO:
    # 1. task["image_url"](/media/xray/abc.png) → 실제 파일 경로로 바꾸기, 없으면 error 결과
    # 2. worker/model.py의 predict(), make_heatmap()으로 예측·히트맵
    # 3. 히트맵 이미지를 media/heatmap/에 저장하고 주소(/media/heatmap/xxx.png) 만들기
    # 4. 약속한 결과 dict 돌려주기 (성공: status="success", 실패: status="error")
    ...


# ===== [박유정] 워커 실행 루프 =====
def main() -> None:
    # TODO:
    # 1. worker/model.py의 load_model()로 모델 불러오기 (워커가 켜질 때 한 번)
    # 2. 무한 반복: BRPOP으로 QUEUE_NAME에서 작업 꺼내기 → json으로 읽기
    # 3. handle_task() 결과를 result_channel(task_id)로 PUBLISH
    # 4. 예외가 나도 워커가 죽지 않게 error 결과를 보내고 다음 작업으로
    ...


if __name__ == "__main__":
    main()
