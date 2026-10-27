# 📝 Day01 작업 내역

- 날짜: 2026-10-21
- 브랜치: `main`(템플릿 업로드), `docs/readme-style_261021`
- PR: #1 (→ develop), #2 (develop → main)
- 작업자: 김지연, 김도엽, 박유정, 이명석

## 요약

| 구분 | 개수 | 내용 |
|---|---|---|
| ⚙️ 레포 설정 | 5개 | 레포 생성, 템플릿 업로드, develop 브랜치, 팀원 초대, 브랜치 보호 규칙 |
| 🆕 새로 만든 것 | 1개 | 팀 규칙 문서 |
| ✏️ 수정한 것 | 2개 | README, .gitignore |

## ⚙️ 레포 설정 (GitHub)

### 팀 레포 생성과 템플릿 업로드

- **무엇을**: Public 레포 `elin-115/Oz_codingSchool`을 만들고, OZ 템플릿(`AH_web_development_assignment`)을 clone해 `main`에 push했다.
- **왜**: 과제 1-1, 1-2. 팀이 함께 쓸 원격 저장소가 필요하다.
- **어떻게**: 템플릿을 clone한 뒤 `git remote set-url origin`으로 원격 주소를 팀 레포로 바꿔 push했다. clone한 그대로 두면 OZ 레포로 push하려다 권한 오류가 난다.

### `develop` 브랜치 생성과 기본 브랜치 설정

- **무엇을**: `main`에서 `develop` 브랜치를 만들고 GitHub 기본 브랜치를 `develop`으로 바꿨다.
- **왜**: 팀 규칙상 개발 기간에는 `develop`을 기준으로 작업한다. 기본 브랜치가 `develop`이면 clone할 때 바로 `develop`이 잡히고, PR의 기본 대상도 `develop`이 되어 실수로 `main`에 PR을 올리는 일을 막는다.

### 팀원 Collaborator 초대

- **무엇을**: 박유정(@RJ-Park), 김도엽(@yeobbro), 이명석(@fpemghs)을 초대했고 전원 수락했다.
- **왜**: 과제 1-3. 초대받아야 push, PR, merge를 할 수 있다.

### 브랜치 보호 규칙 (Ruleset)

- **무엇을**: `main`, `develop`에 Ruleset을 적용했다.
  - Pull Request 필수, 승인 1명 이상
  - 브랜치 삭제 제한, force push 차단
- **왜**: 규칙을 문서로만 두면 실수로 직접 push하는 일이 생긴다. 설정으로 막아서 팀 규칙이 자동으로 지켜지게 했다.
- **어떻게**: Settings → Rules → Rulesets에서 `main`, `develop` 패턴을 대상으로 만들었다. 레포가 Public이라 무료 플랜에서도 적용된다.

## 🆕 새로 만든 것

### `docs/day01_team_rules.md` - 팀 규칙 문서

- **무엇을**: 팀원 명단, 팀 규칙, Git 협업 규칙, 커밋 컨벤션, 커밋하지 않는 파일을 정리했다.
- **왜**: 처음에는 README에 넣었지만, 과제가 날짜별 문서(`docs/dayXX_...md`) 형식을 요구해 분리했다.
- **어떻게**
  - **팀원**: 이름과 GitHub 아이디 표 (팀장 표시 포함)
  - **팀 규칙**: 코어 타임, 1일 1커밋, 존중하는 말투, 일정 공유, 적극 참여
  - **Git 규칙**: `main`은 최종 시점에만, `develop`에 직접 push 금지, 브랜치명 `feature/기능명_YYMMDD`
  - **작업 순서**: develop 최신화 → 브랜치 생성 → 동기화 → push → PR → 승인 후 merge (명령어 포함)
  - **커밋 컨벤션**: `feat`, `fix`, `docs`, `refactor`, `style`, `chore` 표와 예시
  - **단순 수정 기준**: 결과가 달라졌으면 `fix`, 코드만 정리했으면 `refactor`/`style`, 문서 오타는 `docs`

## ✏️ 수정한 것

### `README.md` - 프로젝트 소개와 팀 규칙 링크

- **왜**: 템플릿 README에는 Alembic 가이드만 있어 어떤 프로젝트인지 알 수 없었다.
- **어떻게**: 맨 위에 프로젝트 한 줄 소개와 팀 규칙 문서 링크를 추가했다. 기존 Alembic 가이드는 그대로 두었다.

### `.gitignore` - 모델 가중치 제외

- **왜**: 폐렴 판독 모델의 가중치 파일(`.pth`, `.pt`)은 용량이 커서 저장소에 올리면 안 된다.
- **어떻게**: `*.pth`, `*.pt`를 추가했다. 가중치는 팀 공유 드라이브로 주고받기로 했다.

```diff
+ # Model weights
+ *.pth
+ *.pt
```

## ✅ 확인한 것

| 항목 | 결과 |
|---|---|
| Public Repository | ✅ |
| 팀원 Collaborator 등록 | ✅ 3명 수락 |
| `main`에 템플릿 push | ✅ |
| `main`, `develop` 직접 push 차단 | ✅ Ruleset 적용 |
| 팀 규칙 문서 `main` 반영 | ✅ PR #2 |

## 💬 팀 결정 사항

- 문서 세팅은 팀장이 바로 반영하고, **실제 코드 작업부터 PR 리뷰 규칙**을 적용한다.
- 팀원은 공지에 따라 팀 레포를 clone하고 `git remote -v`로 주소를 확인한다.
