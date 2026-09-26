# 정적 검사 CI

이 첫 CI 단위는 클라우드 연결이나 기존 배포 파일 수정 없이 저장소를 검사한다.
Terraform·Helm 스냅샷과 취약점 스캐너는 별도 변경으로 추가할 예정이다.

## 구성

| 파일 | 역할 |
| --- | --- |
| `.github/workflows/static.yml` | 도구 설치, Actions 문법·셸·시크릿 검사, 보고서 업로드 |
| `ci/static.py` | 셸 문법·ShellCheck와 민감 파일명 검사 |
| `ci/snapshot.py` | 알려진 경고 기준과 비교하고 diff·Summary 생성. 이후 구성 비교에서도 재사용 |
| `tests/baselines/shellcheck.json` | 기존 셸의 경고·정보 15건을 명시적으로 기록 |
| `tests/test_static_ci.py` | 기준 비교·자동 갱신 차단·민감 파일 규칙 테스트 |

## 검사 내용

- `actionlint`: GitHub Actions YAML·표현식·run 명령 검사.
- `bash -n`: 기존 배포 셸의 문법 검사. 셸을 실제 실행하지 않는다.
- `ShellCheck 0.9.0`: 셸 정적 분석. 기존 SC2016/SC2046/SC2086 경고·정보
  15건은 기준 파일과 비교한다. 새로운 경고나 위치·내용 변경은 실패한다.
  error 수준은 기준에 기록하더라도 실패한다. 경고가 없다는 뜻은 아니다.
- 민감 파일명: Git에 추적되는 state·plan·tfvars·개인 키 등을 거부한다.
  provider lock 파일은 허용한다. 이는 파일명 검사이며 모든 비밀 파일을 판별하지 않는다.
- `Gitleaks 8.24.3`: 현재 추적 파일과 Git 전체 이력의 비밀값 패턴 검사.
  `--redact`로 탐지값을 로그에 그대로 출력하지 않는다.
- Python 표준 라이브러리 테스트: 비교기의 일치·불일치 처리와 민감 파일 규칙 확인.

기존 스크립트의 실패 처리나 배포 동작은 수정·검증하지 않는다.
CI 경고 기준은 기존 문제를 숨기는 전체 제외 규칙이 아니라 이번 리뷰 대상인 목록이다.

## 실행과 결과

PR 생성·업데이트, main/master push, 수동 실행에서 동작한다.
일반 작업 브랜치 push만으로는 동작하지 않으므로 포크 내부 PR로 사전 확인할 수 있다.
수동 실행은 기본 브랜치에 워크플로가 존재해야 한다.

Actions가 Ubuntu runner에서 고정 버전 actionlint·ShellCheck·Gitleaks를 다운로드하고
SHA256을 확인한다. AWS 계정·state·클러스터·추가 Python 패키지는 필요하지 않다.
GitHub Actions 사용 권한과 GitHub 다운로드 네트워크가 필요하다.

경고 목록과 diff는 Summary 및 `static-reports` artifact에 남으며 7일간 보관한다.
Gitleaks 결과는 job 로그에 표시된다. 기준이 바뀌었다면 내용을 검토한 뒤
코드와 기준 파일을 같은 PR에서 갱신한다. CI는 기준을 자동 수정하거나 커밋하지 않는다.

필요한 도구가 설치된 경우 선택적으로 로컬 실행할 수 있다.

```bash
python3 -m unittest discover -s tests -p 'test_static_ci.py' -v
python3 ci/static.py
# 의도한 경고 기준 변경을 검토한 경우에만
python3 ci/static.py --update
```

머지를 차단하려면 저장소 ruleset에서 `Static checks / static` 검사를 필수로 설정한다.
워크플로 추가만으로 저장소 ruleset이 설정되지는 않는다.

## 후속 단위

- Terraform validate·mock 구성 스냅샷.
- Helm 렌더링·스키마·구성 스냅샷.
- TODO: 이미지·도구 CVE 검사, IaC 보안 스캐너와 정책.
