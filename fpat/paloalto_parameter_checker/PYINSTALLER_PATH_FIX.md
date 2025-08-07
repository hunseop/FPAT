# PyInstaller 경로 문제 해결

## 🐛 발생한 문제

PyInstaller로 빌드된 실행 파일에서 리포트 다운로드 시 오류 발생:
- **생성 위치**: 현재 실행 경로의 `reports/` 디렉토리
- **찾는 위치**: `_internal/reports/` 디렉토리
- **결과**: 파일을 찾지 못해 다운로드 실패

## 🔍 원인 분석

### PyInstaller 경로 동작 방식
1. **개발 환경**: 스크립트 파일이 있는 디렉토리가 기준
2. **빌드 환경**: 실행 파일이 있는 디렉토리가 기준
3. **상대 경로 문제**: `reports/`, `data/`, `templates/` 등이 잘못된 위치에서 찾아짐

### 구체적 문제점
```python
# 개발 환경: 정상 동작
reports_dir = "reports"  # → ./reports/

# PyInstaller 빌드: 문제 발생  
reports_dir = "reports"  # → ./_internal/reports/ (잘못된 경로)
```

## 🔧 해결 방법

### 1. 공통 유틸리티 함수 생성
**파일**: `utils.py`
```python
def get_base_dir():
    """PyInstaller 빌드 환경에서 올바른 기준 경로 반환"""
    if getattr(sys, 'frozen', False):
        # PyInstaller로 빌드된 실행 파일인 경우
        return os.path.dirname(sys.executable)
    else:
        # 개발 환경인 경우
        return os.path.dirname(os.path.abspath(__file__))

def get_resource_path(relative_path):
    """리소스 파일의 절대 경로 반환 (PyInstaller 호환)"""
    base_dir = get_base_dir()
    return os.path.join(base_dir, relative_path)
```

### 2. 각 모듈별 수정사항

#### ReportGenerator (`report.py`)
```python
# 수정 전
self.reports_dir = reports_dir

# 수정 후  
self.reports_dir = ensure_dir(get_resource_path(reports_dir))
```

#### DatabaseManager (`database.py`)
```python
# 수정 전
self.db_path = db_path

# 수정 후
self.db_path = get_resource_path(db_path)
```

#### ParameterManager (`parameter_manager.py`)
```python
# 수정 전
self.default_params_file = "data/default_params.json"

# 수정 후
self.default_params_file = get_resource_path("data/default_params.json")
```

#### Flask App (`app.py`)
```python
# 수정 전
app = Flask(__name__)

# 수정 후
template_dir = get_resource_path('templates')
static_dir = get_resource_path('static')
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
```

## ✅ 해결 효과

### 경로 문제 완전 해결
- ✅ **리포트 다운로드**: 올바른 경로에서 파일 생성/검색
- ✅ **데이터베이스**: 실행 파일 위치에 데이터 저장
- ✅ **템플릿/정적 파일**: Flask가 올바른 위치에서 리소스 로드
- ✅ **기본 설정 파일**: 패키지된 리소스 정상 접근

### 개발/배포 환경 호환성
- 🔄 **개발 환경**: 기존과 동일하게 정상 동작
- 🔄 **PyInstaller 빌드**: 실행 파일 기준으로 정상 동작
- 🔄 **크로스 플랫폼**: Windows/Linux/Mac 모두 동일하게 동작

## 📁 파일 구조 (수정 후)

### 개발 환경
```
paloalto_parameter_checker/
├── app.py
├── utils.py           # 새로 추가
├── reports/           # 리포트 저장
├── data/              # 데이터베이스
├── templates/         # HTML 템플릿
└── static/            # CSS, JS
```

### PyInstaller 빌드 후
```
ParameterChecker/
├── ParameterChecker.exe
├── utils.py           # 패키지됨
├── reports/           # 실행파일 위치에 생성
├── data/              # 실행파일 위치에 생성  
├── templates/         # 패키지됨
├── static/            # 패키지됨
└── _internal/         # PyInstaller 내부 파일들
```

## 🎯 핵심 포인트

### sys.frozen 활용
```python
if getattr(sys, 'frozen', False):
    # PyInstaller 빌드 환경
    base = os.path.dirname(sys.executable)
else:
    # 개발 환경
    base = os.path.dirname(os.path.abspath(__file__))
```

### 경로 통일화
- 모든 모듈에서 `get_resource_path()` 사용
- 상대 경로 → 절대 경로 변환으로 안정성 확보
- 개발/배포 환경 자동 감지

### 디렉토리 자동 생성
```python
def ensure_dir(dir_path):
    os.makedirs(dir_path, exist_ok=True)
    return dir_path
```

이제 PyInstaller로 빌드한 실행 파일에서도 리포트 다운로드가 정상적으로 작동합니다! 🎉