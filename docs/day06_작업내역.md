# 📝 Day06 작업 내역

- 날짜: 2026-10-28
- PR: #46 ~ (작성 중)
- 작업자: 김지연, 김도엽, 박유정, 이명석

## 요약

| 구분 | 개수 | 내용 |
|---|---|---|
| 🆕 새로 만든 것 | 7개 | 설계 문서, `worker/model.py`, AI 예측 schemas·repositories·services·apis, 마이그레이션 |
| ✏️ 수정한 것 | 4개 | main(lifespan·라우터), 파일 공통 함수, AI 결과 모델(`heatmap_url`), 의존성(torch) |
| 🤖 사용 모델 | 1개 | 김지연 3모델 앙상블(EfficientNet-B0 + ResNet50 + DenseNet121) 중 fold1 |
| 🔌 완성한 API | 0 / 2개 | AI 폐렴 예측, AI 예측 결과 목록 (작성 중) |

| PR | 내용 | 담당 |
|---|---|---|
| #46 | AI 예측 API 설계 + 뼈대 | 김지연 |
| #47 | AI 모델 불러오기·폐렴 예측 (`worker/model.py`) + 모델 결정 | 김지연 |
| | AI 폐렴 예측 `POST /predict` | 김도엽 |
| | AI 예측 결과 목록 `GET /analyses` | 박유정 |
| | 프론트 예측 결과 표 ID·히트맵 열 + 통합 테스트 | 이명석 |

## 🆕 새로 만든 것

### `docs/day06_AI예측_API_설계.md` - AI 예측 API 설계 (과제 2)

- **왜**: 과제 2. 요구사항 정의서(REQ-PRED-001, 002, NFR-PRED-001, 002)를 바탕으로 API 명세 작성
- **어떻게**: Day05와 같은 형식(개요 → 요청 → 응답 → 비고)으로 API 9·10 정리  
주소와 응답 필드는 프론트(`static/apis.js`, `static/pages.js`)가 이미 부르고 읽는 형식에 맞춤

| 결정 | 내용 | 이유 |
|---|---|---|
| 권한 | 승인된 회원 전체 (`StaffUser`) | 요구사항의 "의료인, 개발팀, 연구자"가 세 부서 전부 |
| 결과 재사용 | 진료기록 + 모델 이름(`ai_model`)이 같으면 추론 없이 저장된 결과 응답 (새로 예측 201 / 재사용 200) | 요구사항 "같은 모델로 저장된 결과가 있으면 추론하지 않음" |
| confidence | 예측한 쪽의 확률(%), 0~100 | 폐렴 0.93 → 93.0, 폐렴 0.20(정상) → 80.0 |
| 히트맵 URL | DB `heatmap_url`을 NULL 허용으로 바꾸고 지금은 `null` | 요구사항상 선택사항인데 기존 컬럼이 `NOT NULL` |
| 모델 불러오기 | 서버가 켜질 때 한 번만 (`lifespan`) | 요청마다 파일을 읽으면 3초 응답(NFR-PRED-002)을 지키기 어려움 |
| 모델 파일 | 깃에 올리지 않고 드라이브로 공유 | `*.pt`는 `.gitignore`, GitHub는 100MB 넘는 파일을 막음 |

### 뼈대 (#46)

- **왜**: Day05처럼 공통 부분을 먼저 merge해야 팀원이 같은 기준으로 바로 작업 가능
- **어떻게**
  - `app/schemas/ai_analyses.py`: 공통 응답 `AIAnalysisResponse`. DB의 `Decimal`은 JSON에 문자열(`"93.25"`)로 나가서 `confidence`를 `float`로 받음
  - `app/apis·services·repositories/ai_analyses.py`: 담당별 섹션([김도엽] predict, [박유정] analyses)과 처리 순서 힌트
  - 주소는 진료기록 아래(`/medical-records/{id}/...`)지만 파일은 따로 둠. 담당이 다른 코드가 한 파일에 몰리지 않게
  - `worker/model.py`: `predict()`의 입력·출력(`PredictionResult`)을 먼저 정해, 모델 코드가 끝나기 전에도 API 작업 가능
  - 마이그레이션 `a1c3e5f7b9d2`: `heatmap_url` NULL 허용

### `worker/model.py` - AI 모델 불러오기·폐렴 예측 (김지연, #47, 과제 1)

| 함수 | 하는 일 |
|---|---|
| `build_model(name)` | 학습 때와 같은 구조(EfficientNet-B0 / ResNet50 / DenseNet121, 마지막 층 2개) 생성. `weights=None`으로 ImageNet 가중치는 받지 않음 |
| `load_model()` | `best_model_{모델}_fold1.pt` 3개를 CPU로 불러와 `eval()` 후 전역 리스트에 저장. 파일이 하나라도 없으면 서버는 켜지고 예측만 503 |
| `letterbox` → `crop_content` → `eval_tf` | 학습 노트북과 같은 전처리: 비율 유지 224 → 검은 띠 제거 후 224로 늘리기 → 3채널 → ImageNet 정규화 |
| `predict(image_path)` | 모델마다 원본 + 좌우반전 폐렴 확률 평균 → 3개 평균 → 0.5 이상이면 폐렴 |

- `torch.load(..., map_location="cpu", weights_only=True)`: GPU에서 저장한 파일도 CPU에서 열고, 파일 안의 코드는 실행하지 않음
- 모델 3종과 fold 수는 `MODEL_NAMES`, `FOLDS` 상수로 빼서 구성을 한 줄로 바꿀 수 있게 함

| 테스트 | 결과 |
|---|---|
| 모델 파일 구조 | 15개 모두 `All keys matched successfully` |
| 모델 파일 없음 | 서버 켜짐, `predict()`는 `ModelNotLoadedError` (→ 503) |
| 전처리 | test 사진(1936×1554) → `[3, 224, 224]` |
| 예측 (test 30장) | 최종 제출과 29/30 일치, 1장 평균 0.89초 (최대 1.09초) |
| 서버 시작 | 터미널에 `[AI 모델] ensemble_3models_fold1_v1 불러오기 완료 (3개)` |

## 🤖 모델 비교와 결정

인공지능 트랙 흉부 X-Ray 해커톤 모델 4개와 샘플 모델을 비교함. 자세한 표는 [설계 문서 6장](day06_AI예측_API_설계.md)

| 모델 | 담당 | 리더보드 | 검증 Recall | 서버 적용 |
|---|---|---|---|---|
| **3모델 앙상블 (EfficientNet-B0 + ResNet50 + DenseNet121)** | **김지연** | **0.9583** | 0.9675 | 파일 15개 있음 |
| ResNet50 + ViT-B/16 | 이명석 | 0.9503 | 없음 | 모델 저장 안 됨 |
| DenseNet121 scratch 5-fold | 김도엽 | 0.9295 | 0.9897 | 파일 5개 있음 |
| ResNet50 전이학습 (Keras) | 박유정 | 0.9151 | 0.9871 | TensorFlow 필요 |
| 샘플 SimpleCNN | - | baseline 0.78대 | - | 280KB |

- **비교 기준**: 리더보드(모두 같은 test 624장 공식 점수). 해커톤 test는 정답이 없고, train은 학습에 써서 다시 잴 수 없음. 외부 데이터(라벨 공개된 원본 test)는 과제에 없어서 쓰지 않음
- 검증 Recall이 더 높은 모델도 있었지만, 무작위로 나눈 검증은 옆 번호 사진(같은 환자)이 학습·검증에 섞여 높게 나옴
- 샘플 모델은 해커톤 baseline과 같은 구조. test에서 정확도·Recall 모두 약 0.80으로 추정돼 Recall 기준(0.90)에 못 미침

### fold1만 사용 (3초 기준)

15개를 다 쓰면 CPU에서 사진 1장에 평균 4.8초가 걸려 NFR-PRED-002(3초)를 넘음

| 구성 | 파일 | 예측 1장 | 최종 제출과 다른 장수 (test 624장) |
|---|---|---|---|
| 3모델 × 5 fold | 15개, 663MB | 4.8초 ❌ | 0 |
| **3모델 × fold1** | **3개, 133MB** | **0.89초** ✅ | **3** |
| ResNet50 + DenseNet121 × 5 fold | 10개, 585MB | 약 1.5초 | 3 |

- EfficientNet-B0가 CPU에서 유독 느림 (1개 0.66초, ResNet50 0.12초, DenseNet121 0.17초)
- 3장이 모두 틀려도 정확도 0.953 이상이라 다른 후보보다 높음
- 모델 이름 `ensemble_3models_fold1_v1`. 구성을 바꾸면 이름도 바꿔야 새로 예측함

## ✏️ 수정한 것

| 파일 | 왜 / 어떻게 |
|---|---|
| `app/main.py` | `lifespan`에서 `load_model()` 호출, `ai_analysis_router` 등록 |
| `app/core/files.py` | `media_url_to_path` 추가: `/media/xray/abc.png` → 실제 파일 경로 (예측할 때 이미지 열기용) |
| `app/models/ai_analysis_results.py` | `heatmap_url` NULL 허용 |
| `pyproject.toml`, `uv.lock` | `torch`, `torchvision`, `pillow` 추가 |

## 👥 팀원 작업

### AI 폐렴 예측 `POST /medical-records/{id}/predict` (김도엽)

- (작성 예정)

### AI 예측 결과 목록 `GET /medical-records/{id}/analyses` (박유정)

- (작성 예정)

### 프론트 예측 결과 표 + 통합 테스트 (이명석)

- (작성 예정)

## 💡 배운 것

- **`.pth`/`.pt`는 학습이 끝난 모델의 숫자(가중치)를 저장한 파일.** `state_dict`로 저장하면 구조 코드가 따로 있어야 불러올 수 있고, 학습 때와 구조가 한 줄이라도 다르면 `load_state_dict`에서 에러가 남
- **서버의 전처리는 학습 때와 똑같아야 함.** 샘플 모델에 정규화를 하나 더 넣었더니 정확도가 0.96에서 0.59로 떨어짐
- **노트북 점수와 서버 조건은 다름.** 해커톤에서는 정확도만 봤지만, 서버에서는 응답 시간·파일 크기·메모리도 기준. 15개 앙상블은 점수는 같아도 3초를 넘어서, 정확도를 거의 잃지 않는 선에서 줄임
- **검증 점수는 나누는 방법에 따라 부풀려짐.** 같은 환자 사진이 학습·검증에 섞이면 검증이 쉬워짐. 같은 test로 공식 채점된 리더보드가 비교 기준으로 더 공정함
- **학습 코드와 서버 코드는 다름.** 노트북 셀을 통째로 옮기면 학습 루프·데이터 분석 코드까지 딸려옴. 서버에는 구조·전처리·예측만 필요함
- **CPU를 많이 쓰는 함수는 `async` 서버를 멈추게 함.** 예측은 `run_in_threadpool`로 따로 돌려야 다른 요청이 기다리지 않음

## ⏭️ 남은 작업

- [x] 설계 문서 + 뼈대 (#46)
- [x] 김지연: `worker/model.py` + 모델 결정 (#47)
- [ ] 김도엽: AI 폐렴 예측
- [ ] 박유정: AI 예측 결과 목록
- [ ] 이명석: 프론트 예측 결과 표 ID·히트맵 열 + 통합 테스트
- [ ] 진료기록 상세 화면 확인 (Day05에서 미뤄둔 것)
- [ ] 히트맵(Grad-CAM) 생성 (선택)
- [ ] develop → main
