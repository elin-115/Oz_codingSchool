import json
import socket
from pathlib import Path
from uuid import uuid4

from PIL import Image

from worker.model import ModelNotLoadedError, load_model, make_heatmap, predict
from worker.redis_client import redis_client
from worker.task_contract import (
    ERROR_IMAGE_NOT_FOUND,
    ERROR_MODEL_NOT_READY,
    ERROR_PREDICT_FAILED,
    MODEL_NAME,
    QUEUE_NAME,
    RESULT_TIMEOUT,
    processing_queue,
    result_channel,
)

# AI 워커 실행 파일 (과제 2-2). 실행: uv run python -m worker.main
# 큐에서 작업을 하나씩 꺼내 폐렴 예측 → 결과를 Publish
# 워커를 여러 개 띄워도 BLMOVE는 작업 하나를 워커 하나에게만 줌 (다중 워커)
# BLMOVE는 꺼낸 작업을 워커별 "작업대"(processing 목록)에 올려두고, 결과를 보낸 뒤에 지움
# → 처리 중에 워커가 죽어도 작업대에 남아 있어서, 다시 켜질 때 큐로 되돌려 이어서 처리함 (미완료 작업 복구)
# 주고받는 JSON 형식·에러 코드(error_code)는 docs/day10_AI워커_분리_설계.md 2장 참고


# media 폴더 위치: 프로젝트 루트/media (app/core/files.py와 같은 곳)
# 워커 이미지에는 app/ 코드가 없으므로 경로 변환·히트맵 저장을 워커 안에 직접 둠
MEDIA_DIR = Path(__file__).resolve().parent.parent / "media"
MEDIA_URL = "/media"


# ===== [박유정] 주소 → 실제 파일 경로 =====
def media_url_to_path(url: str) -> Path | None:
    # /media/xray/abc.png → 프로젝트 루트/media/xray/abc.png
    # /media/로 시작하지 않는 이상한 주소면 None
    if not url.startswith(f"{MEDIA_URL}/"):
        return None
    return MEDIA_DIR / url.removeprefix(f"{MEDIA_URL}/")


# ===== [박유정] 히트맵 저장 =====
def save_heatmap_image(image: Image.Image) -> str:
    # 히트맵을 media/heatmap/{랜덤이름}.png로 저장하고 DB에 넣을 주소를 돌려줌
    folder = MEDIA_DIR / "heatmap"
    folder.mkdir(parents=True, exist_ok=True)  # 폴더가 없으면 만듦
    file_name = f"{uuid4().hex}.png"  # 이름이 겹치지 않게 랜덤 이름
    image.save(folder / file_name)
    return f"{MEDIA_URL}/heatmap/{file_name}"


# ===== [박유정] 작업 하나 처리 =====
def handle_task(task: dict) -> dict:
    task_id = task["task_id"]

    # 1. 주소 → 실제 파일 경로. 파일이 없으면 error 결과
    image_path = media_url_to_path(task["image_url"])
    if image_path is None or not image_path.is_file():
        return {
            "task_id": task_id,
            "status": "error",
            "error_code": ERROR_IMAGE_NOT_FOUND,
            "error": "X-Ray 이미지 파일을 찾을 수 없습니다.",
        }

    # 2. 예측 + 히트맵 (모델이 안 올라왔으면 error 결과)
    try:
        prediction = predict(image_path)
        heatmap = make_heatmap(image_path)
    except ModelNotLoadedError:
        return {
            "task_id": task_id,
            "status": "error",
            "error_code": ERROR_MODEL_NOT_READY,
            "error": "AI 모델이 준비되지 않았습니다.",
        }

    # 3. 히트맵 저장하고 주소 받기
    heatmap_url = save_heatmap_image(heatmap)

    # 4. 약속한 성공 결과
    return {
        "task_id": task_id,
        "status": "success",
        "is_pneumonia": prediction.is_pneumonia,
        "confidence": prediction.confidence,
        "heatmap_url": heatmap_url,
        "ai_model": MODEL_NAME,
    }


# ===== [박유정] 워커 실행 루프 =====
def main() -> None:
    # 1. 워커가 켜질 때 모델을 한 번만 불러옴
    load_model()
    worker_name = socket.gethostname()  # 컨테이너 이름(hostname), 재시작해도 그대로
    processing = processing_queue(worker_name)  # 이 워커 전용 작업대 이름
    print(f"[AI 워커] 시작! {QUEUE_NAME} 에서 작업을 기다리는 중...")

    # 2. 지난번에 처리하다 죽은 작업이 작업대에 남아 있으면 큐로 되돌림 (미완료 작업 복구)
    #    작업대 왼쪽(최신)부터 꺼내 큐 오른쪽에 넣음 → 가장 오래된 작업이 다음 차례가 됨
    recovered = 0
    while redis_client.lmove(processing, QUEUE_NAME, "LEFT", "RIGHT"):
        recovered += 1
    if recovered:
        print(f"[AI 워커] 미완료 작업 {recovered}개 복구")

    # 3. 무한 반복: 작업 하나 꺼내기 → 처리 → 결과 보내기 → 작업대에서 지우기
    while True:
        # 큐에서 꺼내면서 동시에 작업대로 옮김 (원자적이라 중간에 사라지지 않음)
        # 큐가 비어 있으면 작업이 들어올 때까지 여기서 기다림 (timeout=0)
        raw_task = redis_client.blmove(QUEUE_NAME, processing, 0, src="RIGHT", dest="LEFT")

        # 작업대에 유효기간을 걸어둠 → 워커가 새 컨테이너로 바뀌어 버려진 작업대는 Redis가 알아서 지움
        redis_client.expire(processing, RESULT_TIMEOUT * 2)

        task_id = "unknown"  # 메시지가 망가져서 task_id를 못 읽을 때 쓰는 이름
        try:
            task = json.loads(raw_task)  # 글자(JSON) → dict
            task_id = task["task_id"]
            result = handle_task(task)
        except Exception as e:
            # 어떤 에러가 나도 워커는 죽지 않고 error 결과를 보냄
            print(f"[AI 워커] 작업 실패 task_id={task_id}: {e}")
            result = {
                "task_id": task_id,
                "status": "error",
                "error_code": ERROR_PREDICT_FAILED,
                "error": "AI 예측 처리 중 오류가 발생했습니다.",
            }

        # 이 작업의 결과 채널로 보내기 (dict → 글자(JSON))
        redis_client.publish(result_channel(task_id), json.dumps(result))

        # 작업대에서 방금 끝낸 작업 1개 삭제 → 처리 끝 (결과를 보낸 뒤에 지워야 복구가 안전함)
        redis_client.lrem(processing, 1, raw_task)
        print(f"[AI 워커] 완료 task_id={task_id} status={result['status']}")


if __name__ == "__main__":
    main()
