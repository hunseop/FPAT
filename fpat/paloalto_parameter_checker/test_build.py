#!/usr/bin/env python3
"""
빌드 환경 테스트 스크립트
PyInstaller 빌드 전 환경을 검증합니다.
"""

import sys
import os
import importlib
from pathlib import Path

def test_python_version():
    """Python 버전 확인"""
    print("🐍 Python 버전 확인...")
    version = sys.version_info
    print(f"   버전: {version.major}.{version.minor}.{version.micro}")
    
    if version.major >= 3 and version.minor >= 8:
        print("   ✅ Python 3.8+ 요구사항 충족")
        return True
    else:
        print("   ❌ Python 3.8 이상이 필요합니다")
        return False

def test_dependencies():
    """필수 패키지 설치 확인"""
    print("\n📦 필수 패키지 확인...")
    
    required_packages = {
        'flask': 'Flask',
        'flask_cors': 'Flask-CORS', 
        'paramiko': 'Paramiko',
        'openpyxl': 'OpenPyXL',
        'PyInstaller': 'PyInstaller'
    }
    
    all_installed = True
    
    for module_name, display_name in required_packages.items():
        try:
            importlib.import_module(module_name)
            print(f"   ✅ {display_name}")
        except ImportError:
            print(f"   ❌ {display_name} - 설치 필요")
            all_installed = False
    
    return all_installed

def test_file_structure():
    """프로젝트 파일 구조 확인"""
    print("\n📁 프로젝트 파일 구조 확인...")
    
    required_files = [
        'app.py',
        'run.py', 
        'parameter_checker.spec',
        'requirements.txt',
        'requirements-build.txt'
    ]
    
    required_dirs = [
        'templates',
        'static',
        'data'
    ]
    
    all_exists = True
    
    # 파일 확인
    for file_name in required_files:
        if os.path.exists(file_name):
            print(f"   ✅ {file_name}")
        else:
            print(f"   ❌ {file_name} - 누락")
            all_exists = False
    
    # 디렉토리 확인
    for dir_name in required_dirs:
        if os.path.isdir(dir_name):
            print(f"   ✅ {dir_name}/")
        else:
            print(f"   ❌ {dir_name}/ - 누락")
            all_exists = False
    
    return all_exists

def test_app_import():
    """앱 import 테스트"""
    print("\n🔧 애플리케이션 import 테스트...")
    
    try:
        # sys.path에 현재 디렉토리 추가
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        from app import app
        print("   ✅ Flask 앱 import 성공")
        
        # 앱 설정 확인
        if hasattr(app, 'config'):
            print("   ✅ 앱 설정 정상")
        else:
            print("   ⚠️ 앱 설정 확인 필요")
            
        return True
        
    except Exception as e:
        print(f"   ❌ import 실패: {e}")
        return False

def test_spec_file():
    """spec 파일 구문 확인"""
    print("\n📋 spec 파일 구문 확인...")
    
    try:
        with open('parameter_checker.spec', 'r', encoding='utf-8') as f:
            spec_content = f.read()
            
        # 기본적인 구문 검사
        if 'Analysis(' in spec_content:
            print("   ✅ Analysis 섹션 존재")
        else:
            print("   ❌ Analysis 섹션 누락")
            return False
            
        if 'EXE(' in spec_content:
            print("   ✅ EXE 섹션 존재")
        else:
            print("   ❌ EXE 섹션 누락")
            return False
            
        if 'COLLECT(' in spec_content:
            print("   ✅ COLLECT 섹션 존재")
        else:
            print("   ❌ COLLECT 섹션 누락")
            return False
            
        print("   ✅ spec 파일 구문 정상")
        return True
        
    except FileNotFoundError:
        print("   ❌ parameter_checker.spec 파일 없음")
        return False
    except Exception as e:
        print(f"   ❌ spec 파일 읽기 실패: {e}")
        return False

def main():
    """테스트 메인 함수"""
    print("🧪 PyInstaller 빌드 환경 테스트")
    print("=" * 50)
    
    tests = [
        ("Python 버전", test_python_version),
        ("필수 패키지", test_dependencies), 
        ("파일 구조", test_file_structure),
        ("앱 Import", test_app_import),
        ("Spec 파일", test_spec_file)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"   ❌ {test_name} 테스트 실행 실패: {e}")
            results.append((test_name, False))
    
    # 결과 요약
    print("\n📊 테스트 결과 요약")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\n통과: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 모든 테스트 통과! 빌드 준비 완료")
        print("빌드 실행: python build.py")
        return True
    else:
        print(f"\n⚠️ {total - passed}개 테스트 실패")
        print("실패한 항목을 수정 후 다시 테스트하세요")
        return False

if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ 테스트가 중단되었습니다")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 테스트 실행 중 오류: {e}")
        sys.exit(1)