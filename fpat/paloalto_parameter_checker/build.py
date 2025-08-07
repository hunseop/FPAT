#!/usr/bin/env python3
"""
Palo Alto Parameter Checker 빌드 스크립트
PyInstaller를 사용하여 실행 파일 생성
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_dependencies():
    """필요한 패키지들이 설치되어 있는지 확인"""
    required_packages = [
        'pyinstaller',
        'flask',
        'flask-cors',
        'paramiko',
        'openpyxl'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ 다음 패키지들이 설치되지 않았습니다:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n설치 명령어:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

def clean_build():
    """이전 빌드 결과물 정리"""
    print("🧹 이전 빌드 결과물 정리 중...")
    
    paths_to_clean = [
        'build',
        'dist',
        '__pycache__',
        '*.spec'
    ]
    
    for path in paths_to_clean:
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
                print(f"   삭제: {path}/")
            else:
                os.remove(path)
                print(f"   삭제: {path}")

def build_application():
    """PyInstaller로 애플리케이션 빌드"""
    print("🔨 PyInstaller로 빌드 시작...")
    
    # spec 파일 사용하여 빌드
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        '--noconfirm',
        'parameter_checker.spec'
    ]
    
    print(f"실행 명령어: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ 빌드 성공!")
        return True
    except subprocess.CalledProcessError as e:
        print("❌ 빌드 실패!")
        print(f"오류: {e}")
        print(f"stderr: {e.stderr}")
        return False

def create_launcher_script():
    """편리한 실행을 위한 런처 스크립트 생성"""
    print("📝 런처 스크립트 생성 중...")
    
    # Windows용 배치 파일
    bat_content = '''@echo off
echo ================================================
echo 🛡️  Palo Alto Parameter Checker v2.0
echo ================================================
echo 📍 서버 주소: http://localhost:5012
echo 🔗 브라우저에서 위 주소로 접속하세요
echo ================================================
echo.

cd /d "%~dp0"
start "" "http://localhost:5012"
ParameterChecker.exe
pause
'''
    
    with open('dist/ParameterChecker/start.bat', 'w', encoding='utf-8') as f:
        f.write(bat_content)
    
    # Linux/Mac용 셸 스크립트
    sh_content = '''#!/bin/bash
echo "================================================"
echo "🛡️  Palo Alto Parameter Checker v2.0"
echo "================================================"
echo "📍 서버 주소: http://localhost:5012"
echo "🔗 브라우저에서 위 주소로 접속하세요"
echo "================================================"
echo

cd "$(dirname "$0")"

# 브라우저 열기 (백그라운드)
if command -v xdg-open > /dev/null 2>&1; then
    xdg-open "http://localhost:5012" &
elif command -v open > /dev/null 2>&1; then
    open "http://localhost:5012" &
fi

# 애플리케이션 실행
./ParameterChecker
'''
    
    with open('dist/ParameterChecker/start.sh', 'w', encoding='utf-8') as f:
        f.write(sh_content)
    
    # 실행 권한 추가 (Linux/Mac)
    try:
        os.chmod('dist/ParameterChecker/start.sh', 0o755)
    except:
        pass
    
    print("   - start.bat (Windows용)")
    print("   - start.sh (Linux/Mac용)")

def create_readme():
    """사용법 README 파일 생성"""
    print("📄 README 파일 생성 중...")
    
    readme_content = '''# Palo Alto Parameter Checker v2.0

## 실행 방법

### Windows
- `start.bat` 파일을 더블클릭하여 실행

### Linux / macOS
- 터미널에서 `./start.sh` 실행
- 또는 `./ParameterChecker` 직접 실행

## 사용법

1. 프로그램 실행 후 자동으로 브라우저가 열립니다
2. 브라우저에서 http://localhost:5012 접속
3. Palo Alto 장비 정보 입력:
   - Host: 장비 IP 또는 호스트명
   - Username: SSH 사용자명
   - Password: SSH 비밀번호
4. "Check" 버튼 클릭하여 파라미터 점검 실행
5. 결과 확인 및 Excel 리포트 다운로드

## 주요 기능

- 🔍 **파라미터 검색**: 실시간 파라미터 필터링
- 🔐 **보안 강화**: 입력값 검증 및 명령어 화이트리스트
- 📊 **결과 정렬**: FAIL → ERROR → PASS 순서로 우선순위 표시
- 📈 **Excel 리포트**: 점검 결과 Excel 파일 다운로드
- ⚡ **실시간 피드백**: 점검 진행 상황 표시

## 문제 해결

### 포트 충돌
- 5012 포트가 사용 중인 경우 다른 포트 사용
- 프로그램 종료 후 재실행

### 브라우저 접속 안됨
- 수동으로 http://localhost:5012 접속
- 방화벽 설정 확인

### SSH 연결 실패
- 네트워크 연결 확인
- SSH 계정 정보 확인
- 장비 SSH 서비스 상태 확인

## 지원

문제 발생 시 로그 파일과 함께 문의하세요.
'''
    
    with open('dist/ParameterChecker/README.txt', 'w', encoding='utf-8') as f:
        f.write(readme_content)

def main():
    """메인 빌드 프로세스"""
    print("🚀 Palo Alto Parameter Checker 빌드 시작")
    print("=" * 60)
    
    # 1. 의존성 확인
    if not check_dependencies():
        return False
    
    # 2. 이전 빌드 정리
    clean_build()
    
    # 3. 애플리케이션 빌드
    if not build_application():
        return False
    
    # 4. 추가 파일들 생성
    create_launcher_script()
    create_readme()
    
    print("\n✅ 빌드 완료!")
    print("=" * 60)
    print("📦 빌드 결과물: dist/ParameterChecker/")
    print("🚀 실행 방법:")
    print("   Windows: start.bat 더블클릭")
    print("   Linux/Mac: ./start.sh 실행")
    print("=" * 60)
    
    return True

if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ 빌드가 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 빌드 중 오류 발생: {e}")
        sys.exit(1)