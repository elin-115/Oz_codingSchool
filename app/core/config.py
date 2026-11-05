from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_USER: str = "root"
    DB_PASSWORD: str = "password1234"
    DB_HOST: str = "localhost"
    DB_PORT: str = "3306"
    DB_NAME: str = "ai_health"

    # Redis 설정 (AI 예측 작업 대기열, 결과 Pub/Sub). 도커에서는 compose가 REDIS_HOST=redis로 덮어씀
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # JWT 설정 (SECRET_KEY는 반드시 .env에서 바꿔서 사용)
    SECRET_KEY: str = "change-this-secret-key-in-env"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }


settings = Settings()
