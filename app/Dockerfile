# 1. Python 3.13이 깔린 가벼운 리눅스에서 시작
FROM python:3.13-slim

# 1-1. asyncmy 컴파일용 도구 설치 (slim 이미지엔 gcc가 없음)
# apt-get: 리눅스용 설치 도구 (맥의 brew 같은 것)
# build-essential: gcc 같은 컴파일 도구 묶음
# --no-install-recommends: 꼭 필요한 것만
# rm -rf /var/lib/apt/lists/*: 설치 목록 캐시 지워서 이미지 가볍게
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

# 2. uv 설치
RUN pip install uv

# 3. 상자 안 작업 폴더
WORKDIR /app

# 4. 라이브러리 목록 파일만 먼저 복사 → 설치
#    (코드보다 먼저 하면, 코드만 바뀔 땐 설치를 건너뛰어서 빌드가 빨라짐)
# --frozen: uv.lock에 적힌 버전 그대로 설치 (마음대로 업데이트 안 함)
# --no-dev: pytest 같은 개발용 도구는 빼기 (이미지 가볍게)
# 내 컴퓨터 파일을 상자 안으로 복사
COPY pyproject.toml uv.lock ./
# 라이브러리 전부 설치
RUN uv sync --frozen --no-dev       

# 5. 나머지 코드 전부 복사
COPY . .

# 6. 8000번 포트 사용
EXPOSE 8000

# 7. 컨테이너 켤 때 FastAPI 실행
CMD ["uv", "run", "--no-dev", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
