"""
YAML 구조 마이그레이션 도구
기존 4섹션 구조를 새로운 1섹션 구조로 자동 변환
"""

import yaml
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)

def convert_old_to_new_structure(old_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    기존 구조를 새로운 구조로 변환
    
    Args:
        old_config: 기존 4섹션 구조의 설정
        
    Returns:
        new_config: 새로운 1섹션 구조의 설정
    """
    if 'parameters' in old_config:
        logger.warning("이미 새로운 구조입니다.")
        return old_config
    
    required_sections = ['prefix_map', 'expected_values', 'command_prefix_map', 'command_map']
    for section in required_sections:
        if section not in old_config:
            raise ValueError(f"필수 섹션 '{section}'이 없습니다.")
    
    new_config = {
        'parameters': []
    }
    
    # 역추적을 위한 매핑 구성
    prefix_to_param = old_config['prefix_map']  # "CTD mode is:" -> "ctd_mode"
    param_to_expected = old_config['expected_values']  # "ctd_mode" -> "disabled"
    cmd_to_prefixes = old_config['command_prefix_map']  # "show ..." -> ["CTD mode is:", ...]
    cmd_map = old_config['command_map']  # "show ..." -> "show ..."
    
    # 각 파라미터별로 새로운 구조 생성
    processed_params = set()
    
    for api_command, prefixes in cmd_to_prefixes.items():
        for prefix in prefixes:
            param_name = prefix_to_param.get(prefix)
            if param_name and param_name not in processed_params:
                param = {
                    'name': param_name,
                    'expected_value': param_to_expected.get(param_name, ''),
                    'api_command': api_command,
                    'output_prefix': prefix,
                    'description': _generate_description(param_name),
                    'cli_query_command': _generate_cli_query(param_name, api_command),
                    'cli_modify_command': _generate_cli_modify(param_name, param_to_expected.get(param_name, ''))
                }
                new_config['parameters'].append(param)
                processed_params.add(param_name)
    
    logger.info(f"변환 완료: {len(new_config['parameters'])}개 파라미터")
    return new_config

def _generate_description(param_name: str) -> str:
    """파라미터 이름으로부터 설명 생성"""
    descriptions = {
        'ctd_mode': 'Content-ID 확인 모드 설정',
        'rematch': '애플리케이션 재매칭 설정',
        'session_timeout': '세션 타임아웃 설정',
        'log_level': '시스템 로그 레벨',
        'ssl_decrypt': 'SSL 복호화 설정',
        'threat_detection': '위협 탐지 설정',
        'user_id': '사용자 ID 설정',
        'content_inspection': '콘텐츠 검사 설정',
        'tunnel_inspection': '터널 검사 설정'
    }
    return descriptions.get(param_name, f'{param_name} 설정')

def _generate_cli_query(param_name: str, api_command: str) -> str:
    """API 명령어로부터 CLI 조회 명령어 생성"""
    # API 명령어를 CLI 조회 명령어로 변환하는 간단한 매핑
    cli_mappings = {
        'show system setting ctd mode': 'show system setting | match ctd',
        'show config running match rematch': 'show running application setting | match rematch',
        'show system setting session timeout': 'show system setting | match timeout',
        'show system setting log level': 'show system setting | match log-level'
    }
    return cli_mappings.get(api_command, f'# CLI 명령어 미정의: {api_command}')

def _generate_cli_modify(param_name: str, expected_value: str) -> str:
    """파라미터와 기대값으로부터 CLI 수정 명령어 생성"""
    cli_modify_mappings = {
        'ctd_mode': f'set system setting ctd-mode {expected_value}',
        'rematch': f'set application setting rematch {expected_value}',
        'session_timeout': f'set system setting session timeout {expected_value}',
        'log_level': f'set system setting log-level {expected_value}'
    }
    return cli_modify_mappings.get(param_name, f'# CLI 수정 명령어 미정의: set ... {expected_value}')

def backup_original_file(file_path: Path) -> Path:
    """원본 파일 백업"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = file_path.with_suffix(f'.backup_{timestamp}.yaml')
    backup_path.write_text(file_path.read_text(encoding='utf-8'), encoding='utf-8')
    logger.info(f"원본 파일 백업: {backup_path}")
    return backup_path

def migrate_yaml_file(input_path: str, output_path: str = None, backup: bool = True) -> bool:
    """
    YAML 파일 마이그레이션 실행
    
    Args:
        input_path: 입력 파일 경로
        output_path: 출력 파일 경로 (None이면 원본 파일 덮어쓰기)
        backup: 백업 생성 여부
        
    Returns:
        bool: 성공 여부
    """
    input_file = Path(input_path)
    
    if not input_file.exists():
        logger.error(f"입력 파일이 존재하지 않습니다: {input_path}")
        return False
    
    try:
        # 원본 파일 로드
        with open(input_file, 'r', encoding='utf-8') as f:
            old_config = yaml.safe_load(f)
        
        if not old_config:
            logger.error("빈 설정 파일입니다.")
            return False
        
        # 백업 생성
        if backup:
            backup_original_file(input_file)
        
        # 구조 변환
        new_config = convert_old_to_new_structure(old_config)
        
        # 출력 파일 결정
        if output_path:
            output_file = Path(output_path)
        else:
            output_file = input_file
        
        # 새로운 구조로 저장
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(new_config, f, default_flow_style=False, allow_unicode=True, 
                     sort_keys=False, indent=2)
        
        logger.info(f"마이그레이션 완료: {output_file}")
        return True
        
    except Exception as e:
        logger.error(f"마이그레이션 실패: {e}")
        return False

def validate_migration(original_path: str, migrated_path: str) -> bool:
    """
    마이그레이션된 파일이 원본과 동일한 동작을 하는지 검증
    """
    try:
        from fpat.paloalto_parameter_checker.parser import load_expected_config
        
        # 원본 파일 로드 (기존 구조)
        original_config = load_expected_config(original_path)
        
        # 마이그레이션된 파일 로드 (새로운 구조 -> 기존 구조로 변환됨)
        migrated_config = load_expected_config(migrated_path)
        
        # 주요 섹션 비교
        sections_to_compare = ['prefix_map', 'expected_values', 'command_map']
        
        for section in sections_to_compare:
            if original_config.get(section) != migrated_config.get(section):
                logger.error(f"검증 실패: {section} 섹션이 다릅니다.")
                return False
        
        logger.info("검증 성공: 마이그레이션된 파일이 원본과 동일한 동작을 합니다.")
        return True
        
    except Exception as e:
        logger.error(f"검증 중 오류: {e}")
        return False

def main():
    """마이그레이션 도구 메인 함수"""
    parser = argparse.ArgumentParser(
        description="Palo Alto Parameter Checker YAML 구조 마이그레이션 도구"
    )
    parser.add_argument("input_file", help="입력 YAML 파일 경로")
    parser.add_argument("-o", "--output", help="출력 파일 경로 (기본: 원본 파일 덮어쓰기)")
    parser.add_argument("--no-backup", action="store_true", help="백업 파일 생성 안 함")
    parser.add_argument("--validate", action="store_true", help="마이그레이션 후 검증 실행")
    parser.add_argument("-v", "--verbose", action="store_true", help="상세 로그 출력")
    
    args = parser.parse_args()
    
    # 로깅 설정
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("🔄 YAML 구조 마이그레이션 도구")
    print(f"📁 입력 파일: {args.input_file}")
    
    # 마이그레이션 실행
    success = migrate_yaml_file(
        args.input_file,
        args.output,
        backup=not args.no_backup
    )
    
    if not success:
        print("❌ 마이그레이션 실패")
        return 1
    
    output_file = args.output or args.input_file
    print(f"✅ 마이그레이션 완료: {output_file}")
    
    # 검증 실행
    if args.validate:
        print("🔍 마이그레이션 검증 중...")
        if validate_migration(args.input_file, output_file):
            print("✅ 검증 성공")
        else:
            print("❌ 검증 실패")
            return 1
    
    print("🎉 모든 작업 완료!")
    return 0

if __name__ == "__main__":
    exit(main())