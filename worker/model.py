from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch import nn
from torchvision import models, transforms

# 폐렴 예측 모델을 메모리에 올리고, X-Ray 이미지로 폐렴 여부를 예측
# app/main.py가 서버를 켤 때 load_model()을 한 번 부르고, API는 predict()만 부른다.

MODELS_DIR = Path(__file__).resolve().parent / "models"  # 모델 파일(.pt)을 넣는 곳 (커밋 안 됨)

# DB ai_analysis_results.ai_model에 저장되는 이름. 같은 이름의 결과가 있으면 다시 예측하지 않으므로
# 모델·전처리를 바꾸면 이름도 바꿔야 함 (예: ensemble_3models_fold1_v1 → ensemble_3models_v2)
MODEL_NAME = "ensemble_3models_fold1_v1"

# 앙상블에 쓰는 모델 3종과 fold 수. 파일 이름이 best_model_{모델}_fold{k}.pt 형식 (5 fold 중 속도 때문에 fold1만 사용, 설계 문서 3장)
MODEL_NAMES = ["efficientnet_b0", "resnet50", "densenet121"]
FOLDS = 1

# load_model()이 불러온 모델 3개(3종 × fold1)를 담아두는 곳. predict()가 여기서 꺼내 씀
# 앞의 _는 이 파일 안에서만 쓰는 변수라는 표시
_models: list[nn.Module] = []


@dataclass
class PredictionResult:
    is_pneumonia: bool
    confidence: float  # 예측한 쪽의 확률(%), 0~100


class ModelNotLoadedError(Exception):
    # 모델 파일이 없어 load_model()이 모델을 올리지 못했을 때 predict()가 냄 → API는 503
    pass


def build_model(name: str) -> nn.Module:
    # 학습 때와 같은 구조를 만듦 (가중치는 load_model에서 .pt 파일로 채움)
    if name == "efficientnet_b0":
        model = models.efficientnet_b0(weights=None)                            # EfficientNet-B0
        model.classifier[1] = nn.Linear(model.classifier[1].in_features, 2)     # 마지막 층 1000개 클래스 → 2개(정상/폐렴)
    elif name == "resnet50":
        model = models.resnet50(weights=None)                                   # ResNet50
        model.fc = nn.Linear(model.fc.in_features, 2)                           # ResNet의 마지막 층 이름은 fc → 2개 클래스
    else:
        model = models.densenet121(weights=None)                                # DenseNet121
        model.classifier = nn.Linear(model.classifier.in_features, 2)           # DenseNet의 마지막 층 이름은 classifier → 2개 클래스
    return model                                                                # 가중치는 load_model에서 채움


# ===== [김지연] 모델 불러오기 =====
def load_model() -> None:
    # 서버가 켜질 때 app/main.py의 lifespan에서 한 번만 호출됨
    # 요청마다 파일을 읽으면 3초 안에 응답하기 어려워서 미리 메모리에 올려둠

    # 1) 파일이 모두 있는지 먼저 확인
    #    하나라도 없으면 앙상블 결과가 학습 때와 달라지므로 아예 올리지 않음
    #    → 서버는 켜지고, 예측 API만 503 "AI 모델이 준비되지 않았습니다."가 됨
    paths = [
        MODELS_DIR / f"best_model_{name}_fold{k}.pt"
        for name in MODEL_NAMES
        for k in range(1, FOLDS + 1)
    ]
    missing = [path.name for path in paths if not path.exists()]
    if missing:
        print(f"[AI 모델] 파일 {len(missing)}개 없음 → 예측 비활성화: {missing}")
        return

    # 2) 모델 3종 × FOLDS개를 차례로 불러옴
    for name in MODEL_NAMES:
        for k in range(1, FOLDS + 1):
            model = build_model(name)  # 학습 때와 같은 구조 (가중치는 아직 비어 있음)
            # map_location="cpu": 파일이 GPU(mps)에서 저장됐어도 CPU 서버에서 열 수 있게
            # weights_only=True: 가중치 숫자만 읽어서, 파일 안에 코드가 숨어 있어도 실행되지 않게
            state_dict = torch.load(
                MODELS_DIR / f"best_model_{name}_fold{k}.pt", map_location="cpu", weights_only=True
            )
            model.load_state_dict(state_dict)  # 구조에 학습된 가중치를 채움 (구조가 다르면 여기서 에러)
            model.eval()                       # 평가 모드: Dropout을 끄고 BatchNorm은 학습 때 통계를 그대로 씀
            _models.append(model)

    print(f"[AI 모델] {MODEL_NAME} 불러오기 완료 ({len(_models)}개)")


# ===== [김지연] 전처리 (학습 노트북 xray_3models와 똑같이) =====
IMG_SIZE = 224    # 모델에 넣을 이미지 크기


def content_box(a):
    bright = a > 8                                         # 검정(0~8)이 아닌 픽셀
    rows = np.where(bright.mean(axis=1) > 0.05)[0]         # 밝은 픽셀이 5% 넘는 행 = 내용이 있는 행
    cols = np.where(bright.mean(axis=0) > 0.05)[0]         # 내용이 있는 열
    return rows[0], rows[-1] + 1, cols[0], cols[-1] + 1    # 내용의 위, 아래, 왼쪽, 오른쪽 경계


def letterbox(img):
    img = img.copy()                                  # 원본을 건드리지 않도록 복사
    img.thumbnail((IMG_SIZE, IMG_SIZE))               # 비율 유지하며 긴 변을 224로 줄이기 (예: 1600×1000 → 224×140)
    canvas = Image.new("L", (IMG_SIZE, IMG_SIZE), 0)  # 224×224 검은 도화지 ("L"=흑백, 0=검정)
    x = (IMG_SIZE - img.size[0]) // 2                 # 왼쪽 시작 위치 (가운데 정렬)
    y = (IMG_SIZE - img.size[1]) // 2                 # 위쪽 시작 위치 (가운데 정렬)
    canvas.paste(img, (x, y))                         # 가운데에 붙이기 → 남는 곳은 검은 띠
    return canvas


def crop_content(img):
    top, bottom, left, right = content_box(np.asarray(img))    # 내용 영역의 경계 (위의 content_box)
    if bottom - top < 20 or right - left < 20:                 # 내용을 제대로 못 찾으면 그대로
        return img
    img = img.crop((left, top, right, bottom))                 # 내용 부분만 자르기 (검은 띠 제거)
    return img.resize((IMG_SIZE, IMG_SIZE), Image.BILINEAR)    # 224×224에 꽉 채우기


eval_tf = transforms.Compose([
    transforms.Grayscale(3),                                                # 3채널로
    transforms.ToTensor(),                                                  # 텐서 변환
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),     # 같은 정규화 (증강 없음 → 매번 같은 결과)
])


# ===== [김지연] 폐렴 예측 =====
THRESHOLD = 0.5  # 폐렴 확률이 이 값 이상이면 폐렴 (학습·제출 때와 같은 기준)


def predict(image_path: Path) -> PredictionResult:
    # API 9(POST /predict)가 진료기록의 X-Ray 경로를 넘겨서 호출함
    # CPU를 많이 쓰는 일반 함수라 API에서는 run_in_threadpool로 따로 돌림

    # 1) 모델이 안 올라왔으면(파일 없음) 예측할 수 없음 → API가 503으로 바꿔서 응답
    if not _models:
        raise ModelNotLoadedError

    # 2) 학습 때와 똑같이 흑백으로 열고 전처리
    #    letterbox(비율 유지 224) → crop_content(검은 띠 제거 후 224로 늘리기) → eval_tf(3채널·정규화)
    #    unsqueeze(0): 모델은 여러 장을 한 번에 받는 모양이라 앞에 "1장"짜리 차원을 붙임 → [1, 3, 224, 224]
    img = Image.open(image_path).convert("L")
    x = eval_tf(crop_content(letterbox(img))).unsqueeze(0)

    # 3) 모델마다 원본 + 좌우반전(TTA) 폐렴 확률을 구해 평균 (제출 때와 같은 방식)
    #    torch.no_grad(): 예측만 하니까 학습용 기울기 계산을 꺼서 빠르고 메모리도 덜 씀
    probs = []
    with torch.no_grad():
        for model in _models:
            p1 = torch.softmax(model(x), dim=1)[0, 1]                          # 원본의 폐렴 확률 ([0, 1] = 첫 장의 1번 칸 = 폐렴)
            p2 = torch.softmax(model(torch.flip(x, dims=[3])), dim=1)[0, 1]    # 좌우반전 사진의 폐렴 확률 (dims=[3] = 가로 방향)
            probs.append((p1 + p2) / 2)

    # 4) 모든 모델의 확률 평균 = 최종 폐렴 확률 (0~1). .item()으로 텐서 → 파이썬 숫자
    prob = torch.stack(probs).mean().item()

    # 5) 기준값으로 폐렴 여부를 정하고, confidence는 "예측한 쪽"의 확률(%)
    #    예: 폐렴 확률 0.93 → 폐렴, 93.0 / 폐렴 확률 0.20 → 정상, 80.0
    is_pneumonia = prob >= THRESHOLD
    confidence = prob if is_pneumonia else 1 - prob
    return PredictionResult(is_pneumonia=is_pneumonia, confidence=round(confidence * 100, 2))
