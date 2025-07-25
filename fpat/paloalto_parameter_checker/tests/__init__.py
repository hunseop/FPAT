"""
Palo Alto Parameter Checker 테스트 모듈
"""

import os
import sys
from pathlib import Path

# 테스트를 위한 경로 설정
test_dir = Path(__file__).parent
project_root = test_dir.parent.parent.parent
sys.path.insert(0, str(project_root))

# 테스트 데이터 경로
TEST_DATA_DIR = test_dir / "data"
TEST_YAML_DIR = TEST_DATA_DIR / "yaml"
TEST_OUTPUT_DIR = test_dir / "output"

# 테스트 디렉토리 생성
TEST_DATA_DIR.mkdir(exist_ok=True)
TEST_YAML_DIR.mkdir(exist_ok=True)
TEST_OUTPUT_DIR.mkdir(exist_ok=True)

__all__ = ["TEST_DATA_DIR", "TEST_YAML_DIR", "TEST_OUTPUT_DIR"]