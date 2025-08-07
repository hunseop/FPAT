# 🚀 PyInstaller 빌드 가이드

## 개요

이 가이드는 Palo Alto Parameter Checker를 PyInstaller를 사용하여 독립 실행 파일로 빌드하는 방법을 설명합니다.

## 📋 사전 준비사항

### 1. Python 환경
- Python 3.8 이상 필요
- 가상환경 사용 권장

### 2. 의존성 설치
```bash
# 가상환경 생성 (선택사항)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate     # Windows

# 빌드용 패키지 설치
pip install -r requirements-build.txt
```

## 🔨 빌드 방법

### 자동 빌드 (권장)

```bash
# 빌드 스크립트 실행
python build.py
```

### 수동 빌드

```bash
# 1. 이전 빌드 정리 (선택사항)
rm -rf build dist __pycache__

# 2. PyInstaller 실행
pyinstaller --clean --noconfirm parameter_checker.spec
```

## 📁 빌드 결과물

빌드 성공 시 다음과 같은 구조로 파일이 생성됩니다:

```
dist/
└── ParameterChecker/
    ├── ParameterChecker.exe    # 실행 파일 (Windows)
    ├── ParameterChecker        # 실행 파일 (Linux/Mac)
    ├── start.bat              # Windows 런처
    ├── start.sh               # Linux/Mac 런처
    ├── README.txt             # 사용 설명서
    ├── templates/             # HTML 템플릿
    ├── static/                # CSS, JS, 이미지
    ├── data/                  # 기본 설정 파일
    └── _internal/             # 라이브러리 파일들
```

## 🚀 실행 방법

### Windows
```cmd
# 방법 1: 런처 사용 (권장)
start.bat

# 방법 2: 직접 실행
ParameterChecker.exe
```

### Linux / macOS
```bash
# 방법 1: 런처 사용 (권장)
./start.sh

# 방법 2: 직접 실행
./ParameterChecker
```

## ⚙️ 고급 설정

### spec 파일 커스터마이징

`parameter_checker.spec` 파일을 수정하여 빌드 옵션을 조정할 수 있습니다:

```python
# 아이콘 추가
exe = EXE(
    # ... 기존 설정 ...
    icon='icon.ico'  # 아이콘 파일 경로
)

# 단일 파일로 빌드 (크기가 커짐)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,    # 추가
    a.zipfiles,    # 추가  
    a.datas,       # 추가
    [],
    name='ParameterChecker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    onefile=True   # 추가
)
```

### 숨겨진 의존성 추가

모듈 import 오류가 발생하는 경우 `hiddenimports`에 추가:

```python
hiddenimports += [
    'your_missing_module',
    'another_module'
]
```

## 🐛 문제 해결

### 일반적인 문제들

#### 1. 모듈 import 오류
```
ModuleNotFoundError: No module named 'xxx'
```

**해결책**: spec 파일의 `hiddenimports`에 누락된 모듈 추가

#### 2. 템플릿/정적 파일 누락
```
TemplateNotFound: template.html
```

**해결책**: spec 파일의 `datas`에 경로 확인 및 추가

#### 3. DLL 누락 (Windows)
```
ImportError: DLL load failed
```

**해결책**: 
- Visual C++ Redistributable 설치
- 누락된 DLL을 `binaries`에 추가

#### 4. 실행 파일 크기가 너무 큰 경우
**해결책**:
- `upx=True` 사용 (압축)
- 불필요한 모듈 `excludes`에 추가
- 가상환경에서 최소한의 패키지만 설치 후 빌드

### 디버깅 모드

문제 발생 시 디버그 모드로 빌드:

```bash
pyinstaller --debug=all parameter_checker.spec
```

## 📦 배포용 패키징

### ZIP 아카이브 생성

```bash
# Windows
powershell Compress-Archive -Path "dist\ParameterChecker" -DestinationPath "ParameterChecker-v2.0-windows.zip"

# Linux/Mac
tar -czf ParameterChecker-v2.0-linux.tar.gz -C dist ParameterChecker
```

### 설치 프로그램 생성 (Windows)

NSIS 또는 Inno Setup을 사용하여 Windows 설치 프로그램 생성 가능

## 🔧 최적화 팁

### 1. 빌드 시간 단축
- 가상환경에서 최소한의 패키지만 설치
- `--noconfirm` 옵션 사용
- SSD 사용

### 2. 실행 파일 크기 최적화
- `upx=True` 압축 활성화
- 불필요한 모듈 제외
- 리소스 파일 최적화

### 3. 시작 시간 최적화
- `--onedir` 사용 (기본값)
- 필요한 모듈만 import
- 지연 로딩 구현

## 📋 체크리스트

빌드 전 확인사항:

- [ ] 모든 의존성 패키지 설치 완료
- [ ] 가상환경 활성화 (권장)
- [ ] templates, static, data 폴더 존재 확인
- [ ] run.py가 올바르게 app을 import하는지 확인
- [ ] spec 파일의 경로들이 정확한지 확인

배포 전 확인사항:

- [ ] 빌드된 실행 파일이 정상 작동하는지 테스트
- [ ] 브라우저에서 웹 인터페이스 접근 가능한지 확인
- [ ] SSH 연결 및 파라미터 점검 기능 테스트
- [ ] Excel 리포트 다운로드 기능 테스트
- [ ] 런처 스크립트들이 올바르게 작동하는지 확인

## 🆘 지원

빌드 관련 문제가 발생하면:

1. 빌드 로그 확인
2. spec 파일 검토
3. 의존성 설치 상태 확인
4. PyInstaller 공식 문서 참조: https://pyinstaller.org/

성공적인 빌드를 위해 이 가이드를 단계별로 따라해보세요! 🎉