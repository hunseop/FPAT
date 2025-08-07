#!/usr/bin/env python3
"""
공통 유틸리티 함수들
"""

import os
import sys

def get_bundle_dir():
    """PyInstaller 번들 내부 경로 (패키지된 리소스용)"""
    if getattr(sys, 'frozen', False):
        # PyInstaller로 빌드된 실행 파일인 경우
        # _MEIPASS 경로 (임시 압축 해제 경로)
        return sys._MEIPASS
    else:
        # 개발 환경인 경우 스크립트 파일이 있는 디렉토리
        return os.path.dirname(os.path.abspath(__file__))

def get_app_dir():
    """애플리케이션 데이터 디렉토리 (사용자 데이터용)"""
    if getattr(sys, 'frozen', False):
        # PyInstaller로 빌드된 실행 파일인 경우
        # 실행 파일이 있는 디렉토리
        return os.path.dirname(sys.executable)
    else:
        # 개발 환경인 경우 스크립트 파일이 있는 디렉토리
        return os.path.dirname(os.path.abspath(__file__))

def get_resource_path(relative_path):
    """패키지된 리소스 파일의 절대 경로 반환 (templates, static 등)"""
    bundle_dir = get_bundle_dir()
    return os.path.join(bundle_dir, relative_path)

def get_data_path(relative_path):
    """사용자 데이터 파일의 절대 경로 반환 (database, reports 등)"""
    app_dir = get_app_dir()
    return os.path.join(app_dir, relative_path)

def ensure_dir(dir_path):
    """디렉토리가 없으면 생성"""
    os.makedirs(dir_path, exist_ok=True)
    return dir_path