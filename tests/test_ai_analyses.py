from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.db.databases import async_get_db
from app.core.dependencies import get_current_user
from app.core.enums import UserRole
from app.main import app
from app.services import ai_analyses as ai_analysis_service
from worker import model as ai_model

AUTH_HEADERS = {"Authorization": "Bearer integration-test-token"}


@pytest.fixture
def api_client():
    """HTTP API용 테스트 클라이언트와 격리된 인증·DB 의존성을 준비한다."""
    user = SimpleNamespace(id=1, role=UserRole.STAFF, is_active=True)
    db = MagicMock()

    async def override_current_user():
        return user

    async def override_db():
        yield db

    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[async_get_db] = override_db

    # lifespan을 시작하지 않아 테스트 중 실제 AI 가중치 파일을 로드하지 않는다.
    client = TestClient(app)
    try:
        yield client, user, db
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


@pytest.fixture
def prediction_setup(monkeypatch, tmp_path):
    """실제 예측 서비스 흐름은 실행하고 파일·모델·저장소 경계만 대체한다."""
    image_path = tmp_path / "xray.png"
    image_path.write_bytes(b"test image")

    record = SimpleNamespace(
        xray_images=[SimpleNamespace(image_url="/media/xray/test.png")]
    )
    saved_result = SimpleNamespace(
        id=101,
        record_id=7,
        is_pneumonia=True,
        confidence=93.25,
        heatmap_url="/media/heatmap/test.png",
        ai_model=ai_model.MODEL_NAME,
        created_at=datetime(2026, 10, 28, 10, 0, 0),
    )

    get_record = AsyncMock(return_value=record)
    get_existing = AsyncMock(side_effect=[None, saved_result])
    create_analysis = AsyncMock(return_value=saved_result)
    get_analyses = AsyncMock(return_value=[saved_result])
    predict = MagicMock(return_value=SimpleNamespace(is_pneumonia=True, confidence=93.25))
    make_heatmap = MagicMock(return_value=object())

    monkeypatch.setattr(
        ai_analysis_service.medical_record_service, "get_record_or_404", get_record
    )
    monkeypatch.setattr(
        ai_analysis_service.ai_analysis_repository, "get_existing_result", get_existing
    )
    monkeypatch.setattr(
        ai_analysis_service.ai_analysis_repository, "create_analysis", create_analysis
    )
    monkeypatch.setattr(
        ai_analysis_service.ai_analysis_repository,
        "get_analyses_by_record_id",
        get_analyses,
    )
    monkeypatch.setattr(
        ai_analysis_service, "media_url_to_path", lambda _url: image_path
    )
    monkeypatch.setattr(
        ai_analysis_service, "save_heatmap_image", lambda _image: saved_result.heatmap_url
    )
    monkeypatch.setattr(ai_analysis_service.ai_model, "predict", predict)
    monkeypatch.setattr(ai_analysis_service.ai_model, "make_heatmap", make_heatmap)

    return SimpleNamespace(
        image_path=image_path,
        get_record=get_record,
        get_existing=get_existing,
        create_analysis=create_analysis,
        get_analyses=get_analyses,
        predict=predict,
        make_heatmap=make_heatmap,
        result=saved_result,
    )


def test_predict_then_list_and_reuse_saved_result(api_client, prediction_setup):
    """새 예측은 201, 목록에 노출되며 같은 모델의 재요청은 200으로 재사용한다."""
    client, _user, _db = api_client

    response = client.post(
        "/api/v1/medical-records/7/predict", headers=AUTH_HEADERS
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": 101,
        "record_id": 7,
        "is_pneumonia": True,
        "confidence": 93.25,
        "heatmap_url": "/media/heatmap/test.png",
        "ai_model": ai_model.MODEL_NAME,
        "created_at": "2026-10-28T10:00:00Z",  # 응답은 UTC 표시(Z)를 붙여 내보냄
    }
    prediction_setup.predict.assert_called_once_with(prediction_setup.image_path)
    prediction_setup.make_heatmap.assert_called_once_with(prediction_setup.image_path)
    prediction_setup.create_analysis.assert_awaited_once()

    # 첫 예측이 저장된 뒤 목록 API에서도 같은 분석 결과를 확인한다.
    list_response = client.get(
        "/api/v1/medical-records/7/analyses", headers=AUTH_HEADERS
    )
    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == 101
    assert list_response.json()[0]["confidence"] == 93.25

    # 저장된 동일 모델 결과가 있으면 추론·저장을 반복하지 않는다.
    repeated_response = client.post(
        "/api/v1/medical-records/7/predict", headers=AUTH_HEADERS
    )
    assert repeated_response.status_code == 200
    assert repeated_response.json()["id"] == 101
    prediction_setup.predict.assert_called_once()
    prediction_setup.create_analysis.assert_awaited_once()


def test_predict_requires_authentication(api_client):
    client, _user, _db = api_client
    app.dependency_overrides.pop(get_current_user)

    response = client.get("/api/v1/medical-records/7/analyses")

    assert response.status_code == 401


def test_pending_user_cannot_access_prediction_api(api_client):
    client, user, _db = api_client
    user.role = UserRole.PENDING

    response = client.get(
        "/api/v1/medical-records/7/analyses", headers=AUTH_HEADERS
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "관리자 승인 후 이용할 수 있습니다."


def test_predict_returns_404_for_missing_record(api_client, monkeypatch):
    client, _user, _db = api_client

    async def missing_record(*_args, **_kwargs):
        raise HTTPException(status_code=404, detail="진료 기록을 찾을 수 없습니다.")

    monkeypatch.setattr(
        ai_analysis_service.medical_record_service,
        "get_record_or_404",
        missing_record,
    )

    response = client.post(
        "/api/v1/medical-records/999/predict", headers=AUTH_HEADERS
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "진료 기록을 찾을 수 없습니다."


@pytest.mark.parametrize(
    "image_url, expected_detail",
    [
        (None, "X-Ray 이미지 파일을 찾을 수 없습니다."),
        ("/media/xray/not-found.png", "X-Ray 이미지 파일을 찾을 수 없습니다."),
    ],
)
def test_predict_returns_404_when_xray_is_missing(
    api_client, monkeypatch, tmp_path, image_url, expected_detail
):
    client, _user, _db = api_client
    record = SimpleNamespace(
        xray_images=(
            []
            if image_url is None
            else [SimpleNamespace(image_url=image_url)]
        )
    )
    monkeypatch.setattr(
        ai_analysis_service.medical_record_service,
        "get_record_or_404",
        AsyncMock(return_value=record),
    )
    monkeypatch.setattr(
        ai_analysis_service.ai_analysis_repository,
        "get_existing_result",
        AsyncMock(return_value=None),
    )
    # 경로는 반환하지만 실제 파일을 만들지 않아 파일 누락 상황을 재현한다.
    missing_path = tmp_path / "missing.png"
    monkeypatch.setattr(
        ai_analysis_service,
        "media_url_to_path",
        lambda _url: missing_path,
    )

    response = client.post(
        "/api/v1/medical-records/7/predict", headers=AUTH_HEADERS
    )

    assert response.status_code == 404
    assert response.json()["detail"] == expected_detail


def test_predict_returns_503_when_model_is_not_loaded(
    api_client, prediction_setup, monkeypatch
):
    client, _user, _db = api_client
    monkeypatch.setattr(
        ai_analysis_service.ai_analysis_repository,
        "get_existing_result",
        AsyncMock(return_value=None),
    )
    prediction_setup.predict.side_effect = ai_model.ModelNotLoadedError

    response = client.post(
        "/api/v1/medical-records/7/predict", headers=AUTH_HEADERS
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "AI 모델이 준비되지 않았습니다."


def test_list_returns_empty_array_when_record_has_no_analyses(
    api_client, monkeypatch
):
    client, _user, _db = api_client
    monkeypatch.setattr(
        ai_analysis_service.medical_record_service,
        "get_record_or_404",
        AsyncMock(return_value=SimpleNamespace(id=7)),
    )
    monkeypatch.setattr(
        ai_analysis_service.ai_analysis_repository,
        "get_analyses_by_record_id",
        AsyncMock(return_value=[]),
    )

    response = client.get(
        "/api/v1/medical-records/7/analyses", headers=AUTH_HEADERS
    )

    assert response.status_code == 200
    assert response.json() == []


def test_list_returns_404_for_missing_record(api_client, monkeypatch):
    client, _user, _db = api_client

    async def missing_record(*_args, **_kwargs):
        raise HTTPException(status_code=404, detail="진료 기록을 찾을 수 없습니다.")

    monkeypatch.setattr(
        ai_analysis_service.medical_record_service,
        "get_record_or_404",
        missing_record,
    )

    response = client.get(
        "/api/v1/medical-records/999/analyses", headers=AUTH_HEADERS
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "진료 기록을 찾을 수 없습니다."
