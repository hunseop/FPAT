# 🚀 빠른 빌드 가이드 (spec 파일 없이)

## 📋 간단 빌드 방법

spec 파일 없이도 PyInstaller로 Parameter Checker를 빌드할 수 있습니다!

### 1단계: 패키지 설치

```bash
# 기본 패키지들만 설치
pip install flask flask-cors paramiko openpyxl pyinstaller
```

### 2단계: 자동 빌드

```bash
# 빌드 스크립트 실행 (spec 파일 자동 감지)
python build.py
```

### 3단계: 수동 빌드 (선택사항)

자동 빌드가 안되면 수동으로:

#### Windows:
```cmd
pyinstaller --clean --noconfirm --onedir --console --name=ParameterChecker --add-data=templates;templates --add-data=static;static --add-data=data;data --hidden-import=flask_cors --hidden-import=sqlite3 --hidden-import=openpyxl --hidden-import=paramiko run.py
```

#### Linux/Mac:
```bash
pyinstaller --clean --noconfirm --onedir --console --name=ParameterChecker --add-data=templates:templates --add-data=static:static --add-data=data:data --hidden-import=flask_cors --hidden-import=sqlite3 --hidden-import=openpyxl --hidden-import=paramiko run.py
```

## 📁 결과물

빌드 완료 후:

```
dist/
└── ParameterChecker/
    ├── ParameterChecker.exe    # 실행 파일
    ├── start.bat              # Windows 런처
    ├── start.sh               # Linux/Mac 런처
    ├── README.txt             # 사용법
    └── _internal/             # 라이브러리들
```

## 🚀 실행

- Windows: `start.bat` 더블클릭
- Linux/Mac: `./start.sh` 실행

## 🛠️ 옵션 설명

- `--onedir`: 폴더 형태로 빌드 (권장)
- `--console`: 콘솔 창 표시
- `--name`: 실행 파일 이름
- `--add-data`: 정적 파일 포함
- `--hidden-import`: 자동 감지되지 않는 모듈 추가

## 🎯 핵심 포인트

1. **경로 구분자 주의**: Windows는 `;`, Linux/Mac은 `:` 사용
2. **필수 폴더**: templates, static, data 폴더 필요
3. **숨겨진 import**: Flask 관련 모듈들 수동 추가 필요

이 방법으로 spec 파일 없이도 쉽게 빌드할 수 있습니다! 🎉