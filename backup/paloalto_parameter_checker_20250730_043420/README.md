# Palo Alto Parameter Checker

Palo Alto 방화벽의 파라미터 설정을 점검하고 리포트를 생성하는 도구입니다.

## 주요 기능

- 방화벽 파라미터 설정 점검
- 엑셀/텍스트 형식의 리포트 생성
- CLI 및 API 인터페이스 제공
- YAML 기반의 파라미터 설정 관리

## 모듈 구조

```
paloalto_parameter_checker/
├── api.py           # FastAPI 기반 REST API 서버
├── cli.py           # Click 기반 CLI 인터페이스
├── main.py          # 레거시 CLI 구현 (이전 버전과의 호환성 유지)
├── parser.py        # YAML 설정 파일 및 방화벽 출력 파서
├── reporter.py      # 엑셀/텍스트 리포트 생성기
├── migration_tool.py # YAML 구조 마이그레이션 도구
└── parameters.yaml  # 파라미터 설정 정의 파일
```

## 사용 방법

### API 서버 실행

```bash
# FastAPI 서버 실행
python -m fpat.paloalto_parameter_checker.cli serve
```

### CLI 도구 사용

```bash
# 파라미터 점검 실행
python -m fpat.paloalto_parameter_checker.cli check --hostname <방화벽IP> --username <계정> --password <비밀번호>

# 파라미터 목록 조회
python -m fpat.paloalto_parameter_checker.cli list-parameters

# 파라미터 상세 정보 조회
python -m fpat.paloalto_parameter_checker.cli show-parameter <파라미터이름>
```

### 레거시 CLI 사용 (이전 버전과의 호환성)

```bash
python -m fpat.paloalto_parameter_checker.main --hostname <방화벽IP> --username <계정> --password <비밀번호>
```

## 파라미터 설정 관리

파라미터 설정은 `parameters.yaml` 파일에서 관리됩니다. 설정 파일은 다음과 같은 구조를 가집니다:

```yaml
parameters:
  - name: "ctd_mode"
    description: "Content-ID 확인 모드 설정"
    expected_value: "disabled"
    api_command: "show system setting ctd mode"
    output_prefix: "CTD mode is:"
    cli_query_command: "show system setting | match ctd"
    cli_modify_command: "set system setting ctd-mode disabled"
```

## 빌드

PyInstaller를 사용하여 독립 실행 파일을 생성할 수 있습니다:

```bash
# 빌드 실행
pyinstaller paloalto_parameter_checker.spec
```

빌드 결과물은 `dist/paloalto-parameter-checker` 디렉토리에 생성됩니다. 