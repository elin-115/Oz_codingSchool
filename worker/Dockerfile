FROM python:3.13-slim
# build-essential은 필요 없음 (asyncmy는 app 전용이라 워커엔 안 깔림)
RUN pip install uv
WORKDIR /app

COPY pyproject.toml uv.lock ./
# ai 그룹만
RUN uv sync --frozen --no-default-groups --group ai

# 워커는 worker 폴더만 있으면 됨 - app 코드 필요 없음
COPY worker ./worker

# worker/main.py 실행
CMD ["uv", "run", "--no-sync", "python", "-m", "worker.main"]