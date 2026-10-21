# 🙌 3조 Team Rules

1. 코어 타임(15:10 ~ 16:10)에는 Zep 스터디룸(조교룸 옆)에 모여서 진행합니다.
2. 1일 1커밋: 각자 브랜치에서 하루 1커밋 이상 하고 원격 레포지토리에 푸시합니다.
3. 팀원에게는 항상 존중하는 말투, 존댓말, 쿠션어를 쓰고 호칭은 `OO님`을 사용합니다.
4. 휴가, 결석, 조퇴, 외출 등의 이슈는 꼭 팀 내에 공유합니다.
5. 프로젝트에 적극적으로 참여합니다. 회의에서는 마이크를 켜고 눈치 보지 않고 의견을 말합니다.

## 🤝 Git & GitHub Rules

- `main` 브랜치는 프로젝트 최종 시점에만 merge합니다.
- 개발 기간에는 `develop` 브랜치를 기준으로 작업하고, **`develop`에 직접 push하지 않습니다.**
- 브랜치명: `feature/기능명_YYMMDD` (예: `feature/predict-api_261021`)

### 작업 순서

1. `develop`을 최신화한 뒤 새 브랜치를 생성합니다.
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/기능명_YYMMDD
   ```
2. 작업을 마치면 `develop`을 pull해서 내 브랜치에 merge합니다(동기화).
   ```bash
   git checkout develop
   git pull origin develop
   git checkout feature/기능명_YYMMDD
   git merge develop
   ```
3. 내 브랜치를 push한 뒤 `develop`으로 Pull Request를 올립니다.
   ```bash
   git push origin feature/기능명_YYMMDD
   ```
4. 팀원 1명 이상의 리뷰·승인을 받은 뒤 merge합니다.
5. 충돌이 나면 혼자 해결하지 말고 해당 코드 작성자와 함께 확인합니다.

### 커밋 메시지 컨벤션

| 접두어 | 의미 | 예시 |
|---|---|---|
| `feat:` | 새 기능 추가 | `feat: X-ray 이미지 예측 API 추가` |
| `fix:` | 버그 수정 | `fix: 이미지 업로드 시 500 에러 수정` |
| `docs:` | 문서 수정 | `docs: README에 실행 방법 추가` |
| `refactor:` | 동작 변화 없는 코드 구조 개선 | `refactor: 모델 로딩 코드를 함수로 분리` |
| `style:` | 동작 변화 없는 코드 포맷 수정(띄어쓰기, 들여쓰기 등) | `style: 코드 포맷 정리` |
| `chore:` | 설정, 패키지 등 기타 작업 | `chore: requirements에 torch 추가` |

> 단순 수정이 헷갈리면 **결과가 달라졌는지**로 구분합니다.
> 결과가 달라졌으면 `fix:`, 결과는 그대로이고 코드만 정리했으면 `refactor:` 또는 `style:`, 문서 오타는 `docs:`를 사용합니다.
> `style:`은 CSS 디자인 수정이 아니라 코드 포맷 수정을 뜻합니다.

### 커밋하지 않는 파일

- 모델 가중치(`*.pth`, `*.pt`), `.env`, 가상환경(`.venv`)은 커밋하지 않습니다(`.gitignore`로 관리).
- 모델 가중치는 팀 공유 드라이브로 주고받습니다.
