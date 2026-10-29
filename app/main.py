import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from starlette.staticfiles import StaticFiles
from starlette.responses import FileResponse

from app.apis.admin import admin_router
from app.apis.ai_analyses import ai_analysis_router
from app.apis.medical_records import medical_record_router
from app.apis.patients import patient_router
from app.apis.practice_apis import practice_router
from app.apis.users import user_router
from worker.model import load_model


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버가 켜질 때 AI 모델을 한 번만 메모리에 올림 (요청마다 불러오면 3초 응답을 지키기 어려움)
    load_model()
    yield


app = FastAPI(
    lifespan=lifespan,
    title="폐렴 환자 관리 백오피스",
    # 마크다운은 4칸 이상 들여쓰면 코드 블록이 되므로 description 내용은 들여쓰지 않음
    description="""
흉부 X-Ray 이미지 기반 폐렴 판독 모델을 활용한 환자 관리 백오피스 API

### 👥 3조 팀원
| 이름 | GitHub |
|---|---|
| 김지연 | [@elin-115](https://github.com/elin-115) |
| 박유정 | [@RJ-Park](https://github.com/RJ-Park) |
| 김도엽 | [@yeobbro](https://github.com/yeobbro) |
| 이명석 | [@fpemghs](https://github.com/fpemghs) |
""",
    contact={
        "name": "3조 GitHub Repository",
        "url": "https://github.com/elin-115/Oz_codingSchool",
    },
)

# API 라우터 등록 (아래 catch_all 라우트보다 먼저 등록해야 함)
app.include_router(practice_router)
app.include_router(user_router)
app.include_router(admin_router)
app.include_router(patient_router)
app.include_router(medical_record_router)
app.include_router(ai_analysis_router)

BASE_DIR = Path(__file__).resolve().parent.parent

# 만약 static, media 폴더가 존재하지 않으면 생성
if not (BASE_DIR / "static").exists():
    os.mkdir(BASE_DIR / "static")
if not (BASE_DIR / "media").exists():
    os.mkdir(BASE_DIR / "media")

# 'static' 폴더를 '/static' 경로로 마운트 (CSS, JS 파일 서빙용)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
# 'media' 폴더를 '/media' 경로로 마운트 (사용자 업로드 파일 서빙용)
app.mount("/media", StaticFiles(directory=BASE_DIR / "media"), name="media")


@app.get(path="/healthcheck", status_code=200, include_in_schema=False)
async def healthcheck():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/{path:path}", include_in_schema=False)
async def catch_all(path: str):
    # API나 정적 파일 경로는 제외 (FastAPI가 먼저 매칭하지 못한 경우에만 실행됨)
    if (
        path.startswith("api/v1")
        or path.startswith("static/")
        or path.startswith("media/")
    ):
        from fastapi import HTTPException

        raise HTTPException(status_code=404)
    return FileResponse(BASE_DIR / "static" / "index.html")
