"""
Palo Alto Parameter Checker

Palo Alto 방화벽의 파라미터 설정을 점검하고 리포트를 생성하는 도구입니다.
CLI와 API 인터페이스를 제공하며, YAML 기반의 파라미터 설정 관리를 지원합니다.

주요 기능:
- 방화벽 파라미터 설정 점검
- 엑셀/텍스트 형식의 리포트 생성
- CLI 및 API 인터페이스 제공
- YAML 기반의 파라미터 설정 관리

모듈 구조:
- api.py: FastAPI 기반 REST API 서버
- cli.py: Click 기반 CLI 인터페이스
- main.py: 레거시 CLI 구현
- parser.py: YAML 설정 파일 및 방화벽 출력 파서
- reporter.py: 엑셀/텍스트 리포트 생성기
- migration_tool.py: YAML 구조 마이그레이션 도구
"""

__version__ = '1.0.0'
