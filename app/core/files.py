from pathlib import Path

# 업로드 파일은 서버가 실행되는 환경의 로컬 저장소(media 폴더)에 저장 (REQ-MDR-001)
# app/main.py가 media 폴더를 /media 주소로 열어두므로, 저장한 파일은 /media/... 주소로 접근할 수 있다.
MEDIA_DIR = Path(__file__).resolve().parent.parent.parent / "media"
MEDIA_URL = "/media"


def delete_media_file(url: str) -> None:
    # /media/xray/abc.png → media/xray/abc.png. 이미 없는 파일이면 무시
    if not url.startswith(f"{MEDIA_URL}/"):     # /media/로 시작하지 않는 이상한 주소면 종료
        return
    (MEDIA_DIR / url.removeprefix(f"{MEDIA_URL}/")).unlink(missing_ok=True)
