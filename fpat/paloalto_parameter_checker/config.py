"""
중앙집중식 설정 관리 모듈
환경별 설정, 기본값 관리, 설정 검증 기능 제공
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """데이터베이스 설정"""
    log_file: str = "parameter_checker.log"
    backup_days: int = 7
    max_file_size: str = "10MB"

@dataclass
class NetworkConfig:
    """네트워크 설정"""
    timeout: int = 30
    retry_count: int = 3
    retry_delay: float = 1.0
    ssl_verify: bool = False

@dataclass
class ReportConfig:
    """리포트 설정"""
    excel_engine: str = "openpyxl"
    auto_column_width: bool = True
    max_column_width: int = 50
    include_cli_sheet: bool = True
    save_text_summary: bool = False

@dataclass
class ParameterCheckerConfig:
    """파라미터 체커 메인 설정"""
    yaml_file: str = "parameters.yaml"
    output_dir: str = "."
    backup_configs: bool = True
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    report: ReportConfig = field(default_factory=ReportConfig)

class ConfigManager:
    """설정 관리자"""
    
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self._config = self._load_config()
    
    def _load_config(self) -> ParameterCheckerConfig:
        """설정 로드"""
        config = ParameterCheckerConfig()
        
        # 환경 변수에서 설정 오버라이드
        config.yaml_file = os.getenv('PARAM_YAML_FILE', config.yaml_file)
        config.output_dir = os.getenv('PARAM_OUTPUT_DIR', config.output_dir)
        
        # 네트워크 설정
        config.network.timeout = int(os.getenv('PARAM_TIMEOUT', config.network.timeout))
        config.network.retry_count = int(os.getenv('PARAM_RETRY_COUNT', config.network.retry_count))
        config.network.ssl_verify = os.getenv('PARAM_SSL_VERIFY', 'false').lower() == 'true'
        
        # 리포트 설정
        config.report.include_cli_sheet = os.getenv('PARAM_INCLUDE_CLI', 'true').lower() == 'true'
        config.report.save_text_summary = os.getenv('PARAM_SAVE_TEXT', 'false').lower() == 'true'
        
        logger.debug("설정 로드 완료")
        return config
    
    @property
    def config(self) -> ParameterCheckerConfig:
        """현재 설정 반환"""
        return self._config
    
    def get_yaml_path(self, base_dir: Path) -> Path:
        """YAML 파일 경로 반환"""
        yaml_file = self.config.yaml_file
        
        # 절대 경로인 경우 그대로 사용
        if os.path.isabs(yaml_file):
            return Path(yaml_file)
        
        # 상대 경로인 경우 base_dir 기준
        return base_dir / yaml_file
    
    def get_output_dir(self, base_dir: Path) -> Path:
        """출력 디렉토리 경로 반환"""
        output_dir = self.config.output_dir
        
        if os.path.isabs(output_dir):
            return Path(output_dir)
        
        return base_dir / output_dir
    
    def update_config(self, **kwargs):
        """설정 업데이트"""
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
                logger.debug(f"설정 업데이트: {key} = {value}")
    
    def validate_config(self) -> bool:
        """설정 검증"""
        try:
            # 네트워크 설정 검증
            if self.config.network.timeout <= 0:
                logger.error("타임아웃은 0보다 커야 합니다.")
                return False
            
            if self.config.network.retry_count < 0:
                logger.error("재시도 횟수는 0 이상이어야 합니다.")
                return False
            
            # 리포트 설정 검증
            if self.config.report.max_column_width <= 0:
                logger.error("최대 컬럼 너비는 0보다 커야 합니다.")
                return False
            
            logger.debug("설정 검증 성공")
            return True
            
        except Exception as e:
            logger.error(f"설정 검증 실패: {e}")
            return False
    
    def get_logging_config(self) -> Dict[str, Any]:
        """로깅 설정 반환"""
        return {
            'filename': self.config.database.log_file,
            'maxBytes': self._parse_size(self.config.database.max_file_size),
            'backupCount': self.config.database.backup_days,
            'encoding': 'utf-8'
        }
    
    def _parse_size(self, size_str: str) -> int:
        """크기 문자열을 바이트로 변환"""
        size_str = size_str.upper()
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)

# 전역 설정 관리자 인스턴스
config_manager = ConfigManager()

def get_config() -> ParameterCheckerConfig:
    """설정 반환 (편의 함수)"""
    return config_manager.config

def setup_logging_with_config(verbose: bool = False):
    """설정 기반 로깅 설정"""
    from logging.handlers import RotatingFileHandler
    
    level = logging.DEBUG if verbose else logging.INFO
    log_config = config_manager.get_logging_config()
    
    # 로거 설정
    logger = logging.getLogger()
    logger.setLevel(level)
    
    # 포매터
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 파일 핸들러 (로테이션)
    file_handler = RotatingFileHandler(
        filename=log_config['filename'],
        maxBytes=log_config['maxBytes'],
        backupCount=log_config['backupCount'],
        encoding=log_config['encoding']
    )
    file_handler.setLevel(logging.DEBUG)  # 파일은 항상 디버그 레벨
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    logging.getLogger(__name__).info("로깅 설정 완료")

# 환경별 설정 예시
class DevelopmentConfig(ParameterCheckerConfig):
    """개발 환경 설정"""
    def __init__(self):
        super().__init__()
        self.database.log_file = "dev_parameter_checker.log"
        self.network.timeout = 10
        self.report.save_text_summary = True

class ProductionConfig(ParameterCheckerConfig):
    """운영 환경 설정"""
    def __init__(self):
        super().__init__()
        self.database.log_file = "prod_parameter_checker.log"
        self.database.backup_days = 30
        self.network.timeout = 60
        self.network.retry_count = 5
        self.report.include_cli_sheet = False  # 운영에서는 CLI 정보 제외

def load_environment_config(env: str = None) -> ParameterCheckerConfig:
    """환경별 설정 로드"""
    env = env or os.getenv('PARAM_ENV', 'default')
    
    config_map = {
        'development': DevelopmentConfig,
        'dev': DevelopmentConfig,
        'production': ProductionConfig,
        'prod': ProductionConfig,
        'default': ParameterCheckerConfig
    }
    
    config_class = config_map.get(env.lower(), ParameterCheckerConfig)
    return config_class()