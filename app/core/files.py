from pathlib import Path
from uuid import uuid4


# 업로드 파일은 서버가 실행되는 환경의 로컬 저장소(media 폴더)에 저장
MEDIA_DIR = Path(__file__).resolve().parent.parent.parent / "media"
MEDIA_URL = "/media"
XRAY_FOLDER = "xray"


def save_xray_image(content: bytes, extension: str) -> str:
    # 원래 파일 이름은 겹칠 수 있으므로 UUID로 새 이름을 붙임
    folder = MEDIA_DIR / XRAY_FOLDER
    folder.mkdir(parents=True, exist_ok=True)

    file_name = f"{uuid4().hex}{extension}"
    (folder / file_name).write_bytes(content)

    return f"{MEDIA_URL}/{XRAY_FOLDER}/{file_name}"


def delete_media_file(url: str) -> None:
    # /media/xray/abc.png → media/xray/abc.png
    if not url.startswith(f"{MEDIA_URL}/"):
        return

    (MEDIA_DIR / url.removeprefix(f"{MEDIA_URL}/")).unlink(
        missing_ok=True
    )


def media_url_to_path(url: str) -> Path | None:
    # /media/xray/abc.png → 실제 파일 경로
    if not url.startswith(f"{MEDIA_URL}/"):
        return None

    return MEDIA_DIR / url.removeprefix(f"{MEDIA_URL}/")