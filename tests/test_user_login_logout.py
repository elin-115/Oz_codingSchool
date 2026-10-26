from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.enums import UserRole
from app.services import users as user_service


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def active_user():
    user = MagicMock()
    user.id = 1
    user.email = "test@example.com"
    user.hashed_password = "hashed-password"
    user.is_active = True
    user.role = UserRole.PENDING
    return user


@pytest.mark.asyncio
async def test_login_rejects_unknown_email(mock_db):
    with patch(
        "app.services.users.user_repository.get_user_by_email",
        new_callable=AsyncMock,
        return_value=None,
    ):
        with pytest.raises(HTTPException) as exc:
            await user_service.login(
                mock_db, "unknown@example.com", "Password!1"
            )

    assert exc.value.status_code == 401
    assert exc.value.detail == "이메일 또는 비밀번호가 일치하지 않습니다."


@pytest.mark.asyncio
async def test_login_rejects_wrong_password(mock_db, active_user):
    with (
        patch(
            "app.services.users.user_repository.get_user_by_email",
            new_callable=AsyncMock,
            return_value=active_user,
        ),
        patch("app.services.users.verify_password", return_value=False),
    ):
        with pytest.raises(HTTPException) as exc:
            await user_service.login(
                mock_db, "test@example.com", "WrongPass!1"
            )

    assert exc.value.status_code == 401
    assert exc.value.detail == "이메일 또는 비밀번호가 일치하지 않습니다."


@pytest.mark.asyncio
async def test_login_rejects_inactive_user(mock_db, active_user):
    active_user.is_active = False

    with (
        patch(
            "app.services.users.user_repository.get_user_by_email",
            new_callable=AsyncMock,
            return_value=active_user,
        ),
        patch("app.services.users.verify_password", return_value=True),
    ):
        with pytest.raises(HTTPException) as exc:
            await user_service.login(
                mock_db, "test@example.com", "Password!1"
            )

    assert exc.value.status_code == 403
    assert exc.value.detail == "비활성화된 사용자입니다."
