import asyncio
import json
from uuid import uuid4

from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.files import (
    delete_media_file,
    media_url_to_path,
)
from app.core.predict_lock import (
    acquire_predict_lock,
    release_predict_lock,
)
from app.core.redis_client import redis_client
from app.models import AIAnalysisResult
from app.repositories import ai_analyses as ai_analysis_repository
from app.services import medical_records as medical_record_service

from worker.task_contract import (
    ERROR_IMAGE_NOT_FOUND,
    ERROR_MODEL_NOT_READY,
    ERROR_PREDICT_FAILED,
    MODEL_NAME,
    QUEUE_NAME,
    RESULT_TIMEOUT,
    result_channel,
)


# AI 예측의 비즈니스 규칙을 담당한다.
# 실제 AI 모델 실행 및 히트맵 생성은 별도 Worker가 담당한다.


# ===== [김도엽] AI 폐렴 예측 =====
async def predict_record(
    db: AsyncSession,
    record_id: int,
) -> tuple[AIAnalysisResult, bool]:
    # 1. 진료기록 조회. 없으면 기존 서비스가 404 처리
    record = await medical_record_service.get_record_or_404(db, record_id)

    # 2. 동일 진료기록·모델의 기존 결과 확인
    existing = await ai_analysis_repository.get_existing_result(
        db,
        record_id,
        MODEL_NAME,
    )
    if existing is not None:
        return existing, False

    # 3. X-Ray 이미지 기록 확인
    if not record.xray_images:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="X-Ray 이미지 파일을 찾을 수 없습니다.",
        )

    image_url = record.xray_images[0].image_url

    # 4. 이미지 경로 및 실제 파일 확인
    image_path = media_url_to_path(image_url)
    if image_path is None or not image_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="X-Ray 이미지 파일을 찾을 수 없습니다.",
        )
    # [추가] 5. 동일 진료기록의 중복 예측 방지 Lock
    if not await acquire_predict_lock(record_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 AI 예측이 진행 중입니다.",
        )
    # 동일 진료기록의 중복 예측 방지 Lock
    task_id = str(uuid4())
    channel = result_channel(task_id)

    task = {
        "task_id": task_id,
        "record_id": record_id,
        "image_url": image_url,
    }
    pubsub = None
    heatmap_url = None

    try:
        pubsub = redis_client.pubsub()

        # 6. 결과 채널을 먼저 구독
        # Pub/Sub 메시지 유실 방지를 위해 큐 등록보다 먼저 실행
        await pubsub.subscribe(channel)

        # 7. Redis 작업 대기열에 작업 등록
        await redis_client.lpush(
            QUEUE_NAME,
            json.dumps(task),
        )

        # 8. Worker의 결과 대기
        loop = asyncio.get_running_loop()
        deadline = loop.time() + RESULT_TIMEOUT
        result = None

        while loop.time() < deadline:
            remaining = deadline - loop.time()

            message = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=min(1.0, remaining),
            )

            if message is not None and message.get("data") is not None:
                try:
                    result = json.loads(message["data"])
                except (json.JSONDecodeError, TypeError):
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="AI 워커 결과 형식이 올바르지 않습니다.",
                    ) from None

                break

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="AI 예측 시간이 초과되었습니다.",
            )

        # 9. 작업 ID 확인
        if result.get("task_id") != task_id:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI 워커 결과의 작업 ID가 일치하지 않습니다.",
            )

         # 10. Worker 오류 처리
        if result.get("status") != "success":
            error_message = result.get(
                "error",
                "AI 예측 처리 중 오류가 발생했습니다.",
            )

            error_status_by_code = {
                ERROR_IMAGE_NOT_FOUND: status.HTTP_404_NOT_FOUND,
                ERROR_MODEL_NOT_READY: status.HTTP_503_SERVICE_UNAVAILABLE,
                ERROR_PREDICT_FAILED: status.HTTP_500_INTERNAL_SERVER_ERROR,
            }

            error_status = error_status_by_code.get(
                result.get("error_code"),
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

            raise HTTPException(
                status_code=error_status,
                detail=error_message,
            )

        # 11. Worker 결과 검증
        heatmap_url = result.get("heatmap_url")

        # 히트맵은 선택 항목이므로 None을 허용한다.
        if heatmap_url is not None and (
            not isinstance(heatmap_url, str) or not heatmap_url.strip()
        ):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI 워커의 히트맵 주소가 올바르지 않습니다.",
            )
        if result.get("ai_model") != MODEL_NAME:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI 워커 모델 정보가 일치하지 않습니다.",
            )

        if not isinstance(result.get("is_pneumonia"), bool):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI 워커의 폐렴 예측 결과가 올바르지 않습니다.",
            )

        try:
            confidence = float(result["confidence"])
        except (KeyError, TypeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI 워커의 신뢰도 값이 올바르지 않습니다.",
            ) from None

        if not 0 <= confidence <= 100:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI 워커의 신뢰도 값이 범위를 벗어났습니다.",
            )

        # 12. 예측 결과 DB 저장
        analysis = AIAnalysisResult(
            record_id=record_id,
            is_pneumonia=result["is_pneumonia"],
            confidence=confidence,
            heatmap_url=heatmap_url,
            ai_model=MODEL_NAME,
        )

        saved = await ai_analysis_repository.create_analysis(
            db,
            analysis,
        )

        return saved, True

    except Exception:
        # DB 저장 실패 시 롤백 및 Worker가 생성한 히트맵 삭제
        if heatmap_url:
            try:
                await db.rollback()
            finally:
                await run_in_threadpool(
                    delete_media_file,
                    heatmap_url,
                )
        raise
    finally:
        try:
            if pubsub is not None:
                try:
                    await pubsub.unsubscribe(channel)
                except Exception:
                    pass
                finally:
                    await pubsub.aclose()
        finally:
            await release_predict_lock(record_id)
# ===== [박유정] AI 예측 결과 목록 조회 =====
# 진료기록이 없으면 404 (get_record_or_404), 결과가 없으면 빈 목록 []
async def get_record_analyses(db: AsyncSession, record_id: int) -> list[AIAnalysisResult]:
    # 진료기록 없음 404 "진료 기록을 찾을 수 없습니다." 출력
    await medical_record_service.get_record_or_404(db, record_id)
    # 진료기록 있음(예측 결과 없음) 빈 목록 [] 그대로 출력
    return await ai_analysis_repository.get_analyses_by_record_id(db, record_id)
