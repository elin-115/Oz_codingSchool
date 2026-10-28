from dataclasses import dataclass
from pathlib import Path

# 폐렴 예측 모델을 메모리에 올리고, X-Ray 이미지로 폐렴 여부를 예측한다.
# app/main.py가 서버를 켤 때 load_model()을 한 번 부르고, API는 predict()만 부른다.

MODELS_DIR = Path(__file__).resolve().parent / "models"  # 모델 파일(.pth)을 넣는 곳 (커밋 안 됨)

# DB ai_analysis_results.ai_model에 저장되는 이름. 같은 이름의 결과가 있으면 다시 예측하지 않으므로
# 모델·전처리를 바꾸면 이름도 바꿔야 함 (예: simple_cnn_v1 → simple_cnn_v2)
MODEL_NAME = "TODO"


@dataclass
class PredictionResult:
    is_pneumonia: bool
    confidence: float  # 예측한 쪽의 확률(%), 0~100


class ModelNotLoadedError(Exception):
    # 모델 파일이 없어 load_model()이 모델을 올리지 못했을 때 predict()가 냄 → API는 503
    pass


# ===== [김지연] 모델 불러오기 =====
def load_model() -> None:
    # TODO: 모델 클래스 만들기 → state_dict 불러오기(map_location="cpu", weights_only=True) → eval() → 전역 변수에 저장
    # 모델 파일이 없으면 서버는 켜지되 예측만 503이 되도록 예외를 내지 말고 넘어가기
    pass


# ===== [김지연] 폐렴 예측 =====
def predict(image_path: Path) -> PredictionResult:
    # TODO: 이미지 열기 → 학습 때와 같은 전처리 → 모델 → softmax → 기준값으로 폐렴 여부, confidence 계산
    raise ModelNotLoadedError
