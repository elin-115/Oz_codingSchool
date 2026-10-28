# 🤖 Day06 AI 폐렴 예측 API 설계

## 0. 개요

6일차 사용자 요구사항 정의서(REQ-PRED-001, 002, NFR-PRED-001, 002)를 바탕으로 AI 폐렴 예측 코드와 API를 설계  
API 주소와 응답 필드는 템플릿 프론트엔드(`static/apis.js`, `static/pages.js`)가 호출하고 읽는 형식에 맞춤

- Base URL: `/api/v1`
- 인증: Day04 User API와 동일. 모든 API는 `Authorization: Bearer <access_token>` 헤더가 필요함
- 성능: 모든 API는 3초 이내 응답 (NFR-PRED-002). 모델은 서버가 켜질 때 한 번만 메모리에 올리고, 같은 모델로 저장된 결과가 있으면 추론하지 않음

### API 목록

| # | 기능 | Method | Endpoint | 권한 | 요구사항 | 담당 |
|---|---|---|---|---|---|---|
| 9 | AI 폐렴 예측 | POST | `/api/v1/medical-records/{record_id}/predict` | 승인된 회원 | REQ-PRED-001 | 김도엽 |
| 10 | AI 예측 결과 목록 조회 | GET | `/api/v1/medical-records/{record_id}/analyses` | 승인된 회원 | REQ-PRED-002 | 박유정 |

API 번호는 Day05(1~8)에 이어서 붙임

| 담당 | 할 일 |
|---|---|
| 김지연 | 설계 문서, 공통 뼈대, `worker/model.py` (모델 불러오기·예측), 모델 결과표 정리 → 사용할 모델 결정 |
| 이명석 | 프론트 예측 결과 표에 ID·히트맵 열 추가 (REQ-PRED-002) + AI 예측 통합 테스트 시나리오 작성·실행 |
| 김도엽 | API 9. AI 폐렴 예측 |
| 박유정 | API 10. AI 예측 결과 목록 조회 |
| 모두 | 각자 AI 트랙 모델 결과 공유 (6장 표 형식) |

## 1. 공통 설계

### 1-1. 권한

| 의존성 | 조건 | 사용 API |
|---|---|---|
| `StaffUser` | 대기자(`pending`)가 아닌 회원 | 9, 10 |

- 요구사항의 "사내 의료인, 개발팀, 연구자"는 세 부서 전부라서 **승인된 회원이면 누구나** 사용 가능
- 대기자는 403 `관리자 승인 후 이용할 수 있습니다.`

### 1-2. 공통 코드

| 이름 | 위치 | 용도 |
|---|---|---|
| `load_model` | `worker/model.py` | 서버 시작 시 모델 파일을 읽어 메모리에 올림 (`app/main.py`의 lifespan에서 호출) |
| `predict` | `worker/model.py` | 이미지 경로를 받아 `PredictionResult`(폐렴 여부, confidence) 반환 |
| `MODEL_NAME` | `worker/model.py` | DB `ai_model`에 저장할 모델 이름. 결과 재사용 기준 |
| `make_heatmap` | `worker/model.py` | 이미지 경로를 받아 Grad-CAM 히트맵 이미지(224×224 PNG) 반환 (3장 "히트맵") |
| `save_heatmap_image` | `app/core/files.py` | 히트맵을 `media/heatmap/{uuid}.png`로 저장하고 `/media/heatmap/...` 주소 반환 |
| `AIAnalysisResponse` | `app/schemas/ai_analyses.py` | 예측 결과 응답 (1-3) |
| `media_url_to_path` | `app/core/files.py` | `/media/xray/abc.png` → 실제 파일 경로 |
| `get_record_or_404` | `app/services/medical_records.py` | 진료기록이 없으면 404 (Day05 재사용) |

### 1-3. 예측 결과 응답 형식 (`AIAnalysisResponse`)

```json
{
  "id": 1,
  "record_id": 3,
  "is_pneumonia": true,
  "confidence": 93.25,
  "heatmap_url": "/media/heatmap/3b1f9c....png",
  "ai_model": "ensemble_3models_fold1_v1",
  "created_at": "2026-10-28T10:00:00"
}
```

| 필드명 | 타입 | 설명 |
|---|---|---|
| id | integer | 예측 결과 고유 ID |
| record_id | integer | 진료 기록 ID |
| is_pneumonia | boolean | 폐렴 여부 |
| confidence | number | 예측한 쪽의 확률(%), 0~100, 소수 둘째 자리 |
| heatmap_url | string \| null | Grad-CAM 히트맵 이미지 주소. `<img src>`에 바로 넣음 (만들기 전 결과는 `null`) |
| ai_model | string | 사용한 모델 이름 |
| created_at | string (datetime) | 예측 수행 일시 |

- `confidence`는 DB에서 `Decimal`이라 그대로 두면 JSON에 문자열(`"93.25"`)로 나가므로 스키마에서 `float`로 받음
- 예: 폐렴 확률 0.93 → `is_pneumonia: true`, `confidence: 93.0` / 폐렴 확률 0.20 → `is_pneumonia: false`, `confidence: 80.0`

### 1-4. AI 모델 (`worker/model.py`)

```
worker/
├── __init__.py
├── model.py         # load_model(), predict(), MODEL_NAME
└── models/          # 모델 파일(.pt) 넣는 곳. .gitignore로 커밋 안 됨 → 드라이브 공유
```

- **불러오기**: 서버가 켜질 때 `load_model()`을 한 번 호출해 전역 변수에 저장. 요청마다 파일을 읽으면 3초 안에 응답하기 어려움
- **파일 형식**: 구조 제외 파일(`state_dict`)을 쓰고 `model.py`에 모델 클래스를 직접 작성. 구조 포함 파일(`model.pth`)은 저장한 쪽의 클래스 위치(`__main__`)가 있어야 열려서 서버에서 쓰기 불편함
- **CPU에서 불러오기**: 샘플 파일은 GPU(`cuda:0`)에서 저장되어 `torch.load(..., map_location="cpu", weights_only=True)`로 불러옴. `weights_only=True`는 가중치만 읽어 파일 안의 코드가 실행되지 않게 함
- **전처리는 학습 때와 똑같이**: 크기·흑백/컬러·정규화가 다르면 결과가 틀어짐
- **기준값**: 폐렴 확률이 기준값(기본 0.5) 이상이면 폐렴. Recall ≥ 0.90을 맞추도록 모델 비교 때 함께 정함

**사용 모델 (김지연 3모델 앙상블, fold1)**

| 항목 | 내용 |
|---|---|
| 구조 | EfficientNet-B0, ResNet50, DenseNet121 (torchvision, 마지막 층만 2개로 교체). `build_model()`이 구조를 만들고 `.pt`로 가중치를 채움 |
| 입력 | 224×224, 3채널 |
| 전처리 | 흑백으로 열기 → `letterbox`(비율 유지 224) → `crop_content`(검은 띠 제거 후 224로 늘리기) → `Grayscale(3)` → `ToTensor()` → ImageNet 정규화 |
| 예측 | 모델마다 원본 + 좌우반전 폐렴 확률 평균 → 3개 평균 → 0.5 이상이면 폐렴 |
| 출력 | 2개 값, `softmax` 후 **1번이 폐렴** 확률 |

**샘플 모델 (`model_state_dict.pth`, 비교용)**

| 항목 | 내용 |
|---|---|
| 구조 | SimpleCNN: Conv(1→16) → ReLU → MaxPool → Conv(16→32) → ReLU → MaxPool → Flatten → Linear(32768→2) |
| 입력 | 흑백 1채널, 128×128 |
| 전처리 | `Grayscale()` → `Resize((128, 128))` → `ToTensor()` (Normalize 없음) |
| 출력 | 2개 값, `softmax` 후 **1번이 폐렴** 확률 |

### 1-5. 모델 평가 기준 (NFR-PRED-001)

| 지표 | 기준 | 계산식 |
|---|---|---|
| Recall (민감도) | **0.90 이상** (필수) | TP / (TP + FN) |
| Accuracy | 0.80 이상 (보조) | (TP + TN) / 전체 |

- FN(폐렴 환자를 정상으로 판정)이 가장 위험해서 Recall을 우선으로 봄
- 비교 방법 (6장)
  - **Accuracy**: 해커톤 리더보드 점수. 모두 같은 test 624장으로 채점되어 그대로 비교 가능
  - **Recall**: 리더보드에 없어 각자 노트북의 검증셋 혼동행렬로 계산 (사람마다 검증셋이 달라 참고용)
  - 해커톤 test는 정답 라벨이 없고, train은 학습에 써서 점수가 부풀려지므로 새로 측정하지 않음
  - 같은 기준의 Recall이 필요하면 외부 데이터(라벨 공개된 원본 test) 사용 가능 여부를 조교님께 먼저 확인

---

## 2. API 명세

### API 9. AI 폐렴 예측

#### 1) API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | AI 폐렴 예측 API |
| 설명 | 진료기록 상세 페이지의 `AI 예측 결과보기` 버튼으로, 진료기록에 저장된 X-Ray 이미지를 모델로 예측한다. (REQ-PRED-001) |
| 엔드포인트 | `/api/v1/medical-records/{record_id}/predict` |
| 메서드 | `POST` |
| 인증 필요 여부 | Y (`StaffUser`) |
| 담당 | 김도엽 |

#### 2) 요청 (Request)

**Headers**: `Authorization: Bearer <access_token>`

**경로 파라미터**

| 파라미터명 | 타입 | 필수 (Y / N) | 설명 |
|---|---|---|---|
| record_id | integer | Y | 진료 기록 ID |

**본문 필드 / 쿼리 파라미터**: 없음 (이미지는 진료기록 등록 때 올린 것을 사용)

#### 3) 응답 (Response)

**성공**: 예측 결과 (`AIAnalysisResponse`, 1-3 참고)

| 상태 코드 | 상황 |
|---|---|
| 201 Created | 새로 예측해서 저장함 |
| 200 OK | 같은 진료기록 + 같은 모델로 저장된 결과가 있어 그대로 돌려줌 |

**실패**

| 상태 코드 | 응답 | 상황 |
|---|---|---|
| 401 | `{"detail": "유효하지 않거나 만료된 토큰입니다."}` | 로그인하지 않음 |
| 403 | `{"detail": "관리자 승인 후 이용할 수 있습니다."}` | 대기자 |
| 404 | `{"detail": "진료 기록을 찾을 수 없습니다."}` | 없는 진료기록 |
| 404 | `{"detail": "X-Ray 이미지 파일을 찾을 수 없습니다."}` | 이미지 기록이 없거나 파일이 지워짐 |
| 503 | `{"detail": "AI 모델이 준비되지 않았습니다."}` | `worker/models/`에 모델 파일이 없어 불러오지 못함 |

#### 4) 비고

- 처리 순서
  1. `get_record_or_404`로 진료기록 + X-Ray 이미지 조회
  2. `record_id` + `ai_model == MODEL_NAME`(삭제 표시 제외)으로 저장된 결과가 있으면 **추론하지 않고** 200으로 응답
  3. 없으면 `media_url_to_path`로 이미지 경로를 구해 `predict()` 호출
  4. `make_heatmap()`으로 히트맵을 만들어 `save_heatmap_image()`로 저장 → 주소를 `heatmap_url`에 넣음
  5. 결과를 `ai_analysis_results`에 저장하고 201로 응답. DB 저장이 실패하면 히트맵 파일 삭제 (Day05 진료기록 등록과 같은 방식)
- `predict()`, `make_heatmap()`은 CPU를 쓰는 일반 함수(`def`)라 그대로 부르면 그동안 서버 전체가 멈춤. `await run_in_threadpool(predict, path)`로 따로 돌림 (`from fastapi.concurrency import run_in_threadpool`)
- 같은 결과를 응답하는지는 `Response` 매개변수의 `status_code`를 바꿔서 구분 (`response.status_code = status.HTTP_200_OK`)
- 프론트는 응답 내용을 쓰지 않고, 성공 알림 후 상세 페이지를 다시 그려 API 10으로 목록을 새로 받음

---

### API 10. AI 예측 결과 목록 조회

#### 1) API 개요

| 항목 | 내용 |
|---|---|
| API 이름 | AI 예측 결과 목록 조회 API |
| 설명 | 진료기록 상세 페이지의 AI 예측 결과 섹션에서 해당 진료기록의 예측 결과를 목록으로 조회한다. (REQ-PRED-002) |
| 엔드포인트 | `/api/v1/medical-records/{record_id}/analyses` |
| 메서드 | `GET` |
| 인증 필요 여부 | Y (`StaffUser`) |
| 담당 | 박유정 |

#### 2) 요청 (Request)

**Headers**: `Authorization: Bearer <access_token>`

**경로 파라미터**

| 파라미터명 | 타입 | 필수 (Y / N) | 설명 |
|---|---|---|---|
| record_id | integer | Y | 진료 기록 ID |

**본문 필드 / 쿼리 파라미터**: 없음

#### 3) 응답 (Response)

**성공 · 200 OK**: 예측 결과 목록 (`list[AIAnalysisResponse]`, **최신순**)

```json
[
  {
    "id": 2,
    "record_id": 3,
    "is_pneumonia": true,
    "confidence": 93.25,
    "heatmap_url": null,
    "ai_model": "ensemble_3models_fold1_v2",
    "created_at": "2026-10-28T11:00:00"
  },
  {
    "id": 1,
    "record_id": 3,
    "is_pneumonia": true,
    "confidence": 88.1,
    "heatmap_url": null,
    "ai_model": "ensemble_3models_fold1_v1",
    "created_at": "2026-10-28T10:00:00"
  }
]
```

- 예측 결과가 없으면 빈 목록 `[]` (프론트가 "저장된 예측 결과가 없습니다." 표시)

**실패**

| 상태 코드 | 응답 | 상황 |
|---|---|---|
| 401 | `{"detail": "유효하지 않거나 만료된 토큰입니다."}` | 로그인하지 않음 |
| 403 | `{"detail": "관리자 승인 후 이용할 수 있습니다."}` | 대기자 |
| 404 | `{"detail": "진료 기록을 찾을 수 없습니다."}` | 없는 진료기록 |

#### 4) 비고

- 진료기록이 없으면 404, 진료기록은 있는데 결과만 없으면 `[]` (Day05 API 7과 같은 방식)
- 삭제 표시된 결과(`is_deleted = True`)는 제외
- Day05에 진료기록 상세 화면이 "Not Found"로 안 그려지던 원인이 이 API였음. 이 API가 생기면 화면이 정상으로 그려짐

---

## 3. 요구사항과 다르게 결정한 부분 / 추가로 결정한 부분

### 히트맵: ResNet50 Grad-CAM

- **요구사항**: Hitmap Image URL은 선택사항
- **결정**
  1. DB `heatmap_url`을 `NOT NULL` → **`NULL` 허용** (마이그레이션 `heatmap_url nullable`). 히트맵을 만들기 전 결과도 저장할 수 있게
  2. 히트맵은 **3모델 중 ResNet50(fold1) 하나로** Grad-CAM 생성 (`make_heatmap`)
  3. 모델이 실제로 본 224×224 사진(검은 띠 제거) 위에 중요한 곳일수록 진한 빨간색으로 겹쳐 `media/heatmap/{uuid}.png`로 저장
- **Grad-CAM**: 마지막 합성곱 블록(`layer4`)의 특징맵 × 예측한 쪽 점수의 기울기 → 모델이 판단할 때 중요하게 본 위치
- **이유**
  - ResNet50이 가장 빠르고(0.12초) Grad-CAM 예시가 많은 구조. 3모델을 모두 하면 시간이 3배
  - 예측 + 히트맵 + 저장을 합쳐 1장 약 1.3초 (3초 기준 안)
- **한계**
  - 히트맵의 "예측한 쪽"은 ResNet50 혼자 판단한 결과라, 드물게 3모델 앙상블 결과와 다를 수 있음
  - 원본 사진이 아니라 잘라서 늘린 224×224 사진 위에 그림 (원본 좌표로 되돌리지 않음)
- **동시 요청**: 같은 모델에 훅(hook)이 겹치지 않도록 히트맵은 잠금(`threading.Lock`)으로 한 번에 하나씩 생성
- **삭제**: 환자를 지울 때 X-Ray와 함께 히트맵 파일도 삭제 (Day05 환자 삭제에 추가)

### 권한: 승인된 회원 전체

- 의료인·개발팀·연구자는 모든 부서라 `StaffUser`로 확인 (1-1)

### 결과 재사용 기준: 진료기록 + 모델 이름

- 요구사항 "같은 모델을 사용하여 저장된 예측 결과가 있다면" → `record_id`와 `ai_model`이 같으면 재사용
- 모델을 바꾸면 `MODEL_NAME`도 바꿔야 새로 예측함 (예: `ensemble_3models_fold1_v1` → `ensemble_3models_v2`). 이름만 그대로면 예전 결과가 계속 나옴

### confidence: 예측한 쪽의 확률

- 폐렴이면 폐렴 확률, 정상이면 정상 확률을 % 로 저장 (1-3)

### 모델: 3모델 앙상블 중 fold1만 사용

- **요구사항**: 모든 API 3초 이내 응답 (NFR-PRED-002)
- **결정**: 3모델 × 5 fold(15개) 대신 **3모델 × fold1(3개)** 사용, `MODEL_NAME = "ensemble_3models_fold1_v1"`
- **이유** (CPU, test 사진 1장 기준 측정)

| 구성 | 파일 | 예측 1장 | 최종 제출(0.9583)과 다른 장수 (test 624장) |
|---|---|---|---|
| 3모델 × 5 fold | 15개, 663MB | 평균 4.8초, 최대 6.5초 ❌ | 0 |
| **3모델 × fold1** | **3개, 133MB** | **평균 0.89초, 최대 1.09초** ✅ | **3** |
| ResNet50 + DenseNet121 × 5 fold | 10개, 585MB | 약 1.5초 | 3 |

- EfficientNet-B0가 CPU에서 유독 느림 (1개당 0.66초, ResNet50 0.12초, DenseNet121 0.17초)
- 3장이 모두 틀려도 정확도 0.953 이상이라 다른 후보(0.9503 이하)보다 높음
- fold 수는 `FOLDS` 상수 하나로 바꿀 수 있게 작성 (속도 여유가 생기면 `FOLDS = 5`, 이름은 `_v2`로)

### 모델 파일: 깃에 올리지 않음

- `*.pt`, `*.pth`는 `.gitignore`에 있어 커밋되지 않음. 드라이브로 공유하고 각자 `worker/models/`에 복사
- 필요한 파일: `best_model_efficientnet_b0_fold1.pt`, `best_model_resnet50_fold1.pt`, `best_model_densenet121_fold1.pt`

---

## 4. 코드 구조와 분담

```
worker/
├── model.py                     # [김지연] load_model, predict, make_heatmap, MODEL_NAME
└── models/                      # 모델 파일(.pt), 커밋 안 됨
app/
├── main.py                      # + lifespan에서 load_model(), ai_analysis_router 등록
├── core/files.py                # + media_url_to_path, save_heatmap_image
├── models/ai_analysis_results.py  # heatmap_url nullable
├── schemas/ai_analyses.py       # AIAnalysisResponse
├── repositories/ai_analyses.py  # [김도엽] 저장된 결과 조회·저장 / [박유정] 목록 조회
├── services/ai_analyses.py      # [김도엽] 예측 / [박유정] 목록
└── apis/ai_analyses.py          # /api/v1/medical-records/{record_id}/predict, /analyses
alembic/versions/                # heatmap_url nullable 마이그레이션
static/pages.js                  # [이명석] 예측 결과 표에 ID·히트맵 열 추가
```

- 진료기록과 같은 주소(`/medical-records/...`)지만 파일은 `ai_analyses.py`로 따로 둠. 담당이 다른 코드가 한 파일에 몰리지 않게 하기 위함
- `worker/model.py`가 끝나기 전에도 API 9를 만들 수 있도록 `predict()`의 입력·출력(`PredictionResult`)을 뼈대에서 먼저 정함

---

## 5. 개발 순서

1. 뼈대 PR 머지 후 `git pull`, `uv sync` (torch·torchvision·pillow 추가됨), `uv run alembic upgrade head`
2. 드라이브의 모델 파일을 `worker/models/`에 복사
3. 각자 담당 섹션 작성 → PR
4. 모델 비교 결과로 사용할 모델 확정 → `model.py`의 `MODEL_NAME`·전처리 확정
5. 프론트 진료기록 상세 페이지에서 `AI 예측 결과보기` → 결과 목록 확인

---

## 6. 모델 비교 결과 (김지연 정리)

| 모델 | 담당 | 리더보드 | 검증 Recall | 검증 Accuracy | 입력 크기·전처리 | 파일 크기 |
|---|---|---|---|---|---|---|
| 샘플 SimpleCNN | - | 없음 (같은 구조 baseline 0.7804) | - | - | 흑백 128, 리사이즈, 정규화 없음 | 280KB |
| **3모델 앙상블** (EfficientNet-B0 + ResNet50 + DenseNet121, 5-fold 평균, 좌우반전 TTA) | 김지연 | **0.9583** | 0.9675 | 0.9724 | 224, letterbox → 검은 띠 제거 후 늘리기 → 3채널 → ImageNet 정규화 | 663MB (15개) |
| ResNet50 + ViT-B/16 (soft voting) | 이명석 | 0.9503 | 없음 (검증셋 없음) | 없음 (학습 정확도만) | ResNet50 128 / ViT 224, 3채널 → ImageNet 정규화 | 저장 안 됨 |
| DenseNet121 scratch 5-fold + 스케일 TTA, 기준값 0.335 | 김도엽 | 0.9295 | 0.9897 | 0.9868 | 320, 3채널 → 데이터셋 평균·표준편차 정규화 | 136MB (5개) |
| ResNet50 전이학습 (Keras) | 박유정 | 0.9151 | 0.9871 | 0.9713 | 224 RGB → `preprocess_input` | 98MB (1개) |

- 전처리는 각자 노트북의 `transforms.Compose([...])`를 그대로 옮김 (서버도 똑같이 해야 함)
- 검증 점수는 에포크를 검증 점수로 골라 리더보드보다 높게 나오는 편이라 비교는 리더보드 기준
- 무작위로 나눈 검증(Stratified K-Fold, 홀드아웃)은 옆 번호 사진(같은 환자)이 학습·검증에 섞여 점수가 높게 나옴. 김지연 검증은 10장 묶음으로 나눠 이 누수를 줄임
- **결정: 김지연 3모델 앙상블, 단 fold1 3개만 사용** (팀 논의 10/28)
  1. 리더보드(모두 같은 test 624장 공식 점수) 최고
  2. Recall 0.9675로 기준(0.90) 통과
  3. 모델 파일·전처리 코드가 모두 남아 있음 (김도엽·박유정 모델도 파일은 있지만 점수가 낮고, 박유정 모델은 Keras라 TensorFlow가 따로 필요)
  4. 15개를 모두 쓰면 3초를 넘어 fold1만 사용 (3장 "모델: fold1만 사용")

---

## 📚 참고 자료

- [PyTorch 모델 저장하기 & 불러오기](https://tutorials.pytorch.kr/beginner/saving_loading_models.html)
- [FastAPI Lifespan 이벤트](https://fastapi.tiangolo.com/ko/advanced/events/)
- [FastAPI 응답 상태 코드 바꾸기](https://fastapi.tiangolo.com/ko/advanced/response-change-status-code/)
- [FastAPI 동시성과 async / await](https://fastapi.tiangolo.com/ko/async/)
