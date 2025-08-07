#!/usr/bin/env python3
"""
공통 유틸리티 함수들
"""

import os
import sys

def get_base_dir():
    """PyInstaller 빌드 환경에서 올바른 기준 경로 반환"""
    if getattr(sys, 'frozen', False):
        # PyInstaller로 빌드된 실행 파일인 경우
        # 실행 파일이 있는 디렉토리를 반환
        return os.path.dirname(sys.executable)
    else:
        # 개발 환경인 경우 스크립트 파일이 있는 디렉토리
        return os.path.dirname(os.path.abspath(__file__))

def get_resource_path(relative_path):
    """리소스 파일의 절대 경로 반환 (PyInstaller 호환)"""
    base_dir = get_base_dir()
    return os.path.join(base_dir, relative_path)

def ensure_dir(dir_path):
    """디렉토리가 없으면 생성"""
    os.makedirs(dir_path, exist_ok=True)
    return dir_path