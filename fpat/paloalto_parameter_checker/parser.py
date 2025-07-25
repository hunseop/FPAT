import yaml
import logging
from pathlib import Path

# 로깅 설정
logger = logging.getLogger(__name__)

def validate_yaml_structure(config: dict, yaml_path: str) -> bool:
    """
    YAML 구조의 유효성을 검증하는 함수
    """
    if 'parameters' in config:
        # 새로운 구조 검증
        return _validate_new_structure(config, yaml_path)
    else:
        # 기존 구조 검증
        return _validate_old_structure(config, yaml_path)

def _validate_new_structure(config: dict, yaml_path: str) -> bool:
    """새로운 구조의 유효성 검증"""
    if not isinstance(config.get('parameters'), list):
        logger.error(f"{yaml_path}: 'parameters'는 리스트여야 합니다.")
        return False
    
    required_fields = ['name', 'expected_value', 'api_command', 'output_prefix']
    
    for i, param in enumerate(config['parameters']):
        if not isinstance(param, dict):
            logger.error(f"{yaml_path}: parameters[{i}]는 딕셔너리여야 합니다.")
            return False
        
        for field in required_fields:
            if field not in param:
                logger.error(f"{yaml_path}: parameters[{i}]에 필수 필드 '{field}'가 없습니다.")
                return False
        
        # 파라미터 이름 중복 검사
        param_names = [p['name'] for p in config['parameters']]
        if len(param_names) != len(set(param_names)):
            logger.error(f"{yaml_path}: 중복된 파라미터 이름이 있습니다.")
            return False
    
    logger.info(f"{yaml_path}: 새로운 구조 검증 성공 ({len(config['parameters'])}개 파라미터)")
    return True

def _validate_old_structure(config: dict, yaml_path: str) -> bool:
    """기존 구조의 유효성 검증"""
    required_sections = ['prefix_map', 'expected_values', 'command_prefix_map', 'command_map']
    
    for section in required_sections:
        if section not in config:
            logger.error(f"{yaml_path}: 필수 섹션 '{section}'이 없습니다.")
            return False
    
    logger.info(f"{yaml_path}: 기존 구조 검증 성공")
    return True

def load_expected_config(yaml_path: str) -> dict:
    """
    개선된 설정 로딩 함수 - 에러 처리 및 검증 강화
    """
    yaml_path = Path(yaml_path)
    
    if not yaml_path.exists():
        raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {yaml_path}")
    
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"YAML 파싱 오류: {e}")
    except Exception as e:
        raise ValueError(f"파일 읽기 오류: {e}")
    
    if not config:
        raise ValueError(f"빈 설정 파일입니다: {yaml_path}")
    
    # 구조 검증
    if not validate_yaml_structure(config, str(yaml_path)):
        raise ValueError(f"YAML 구조가 올바르지 않습니다: {yaml_path}")
    
    # 새로운 구조인지 확인
    if 'parameters' in config:
        logger.info(f"새로운 YAML 구조 감지: {len(config['parameters'])}개 파라미터")
        return _convert_new_to_old_structure(config)
    else:
        logger.info("기존 YAML 구조 사용")
        return config

def _convert_new_to_old_structure(new_config: dict) -> dict:
    """
    새로운 구조를 기존 구조로 변환하여 기존 로직이 그대로 작동하도록 함
    """
    old_structure = {
        'prefix_map': {},
        'expected_values': {},
        'command_prefix_map': {},
        'command_map': {}
    }
    
    for param in new_config['parameters']:
        name = param['name']
        
        # prefix_map 구성
        if 'output_prefix' in param:
            old_structure['prefix_map'][param['output_prefix']] = name
        
        # expected_values 구성
        if 'expected_value' in param:
            old_structure['expected_values'][name] = param['expected_value']
        
        # command_map 구성
        if 'api_command' in param:
            old_structure['command_map'][param['api_command']] = param['api_command']
    
    # command_prefix_map은 기존 로직에서 사용되므로 역추적하여 구성
    # API 명령어별로 어떤 파라미터들이 연결되는지 매핑
    for param in new_config['parameters']:
        if 'api_command' in param and 'output_prefix' in param:
            api_cmd = param['api_command']
            if api_cmd not in old_structure['command_prefix_map']:
                old_structure['command_prefix_map'][api_cmd] = []
            old_structure['command_prefix_map'][api_cmd].append(param['output_prefix'])
    
    logger.debug(f"구조 변환 완료: {len(new_config['parameters'])}개 파라미터")
    return old_structure

def parse_command_output(output: str, prefix_map: dict) -> dict:
    """
    개선된 명령어 출력 파싱 함수 - 에러 처리 강화
    """
    if not output:
        logger.warning("빈 출력 데이터")
        return {}
    
    if not prefix_map:
        logger.warning("빈 prefix_map")
        return {}
    
    result = {}
    lines = output

    for line in lines:
        line = line.strip().rstrip(',')
        if not line:  # 빈 라인 스킵
            continue
            
        for prefix, key in prefix_map.items():
            if line.startswith(prefix):
                parts = line.split(": ", 1)
                if len(parts) == 2:
                    value = parts[1].strip()
                    result.setdefault(key, []).append(value)
                    logger.debug(f"파싱 성공: {key} = {value}")
                else:
                    logger.warning(f"파싱 실패 - 잘못된 형식: {line}")
    
    return result

def compare_with_expected(parsed: dict, expected: dict, failed_keys: set) -> list:
    """
    개선된 비교 함수 - 더 상세한 상태 정보 제공
    """
    report = []
    
    for key, exp_value in expected.items():
        exp_value = str(exp_value)
        actual_values = parsed.get(key)

        # 1. 명령어 자체 실패
        if key in failed_keys:
            report.append((key, "명령어 실패", "없음", exp_value))
            logger.warning(f"명령어 실패: {key}")
            continue
        
        # 2. 응답에서 값을 찾을 수 없음
        if actual_values is None:
            report.append((key, "값 없음", "없음", exp_value))
            logger.warning(f"값 없음: {key}")
            continue
        
        # 3. 값 비교
        if isinstance(actual_values, list):
            if all(v == exp_value for v in actual_values):
                report.append((key, "일치", ", ".join(actual_values), exp_value))
                logger.info(f"일치: {key} = {exp_value}")
            else:
                report.append((key, "불일치", ", ".join(actual_values), exp_value))
                logger.warning(f"불일치: {key} - 현재: {actual_values}, 기대: {exp_value}")
        else:
            actual_values = str(actual_values)
            if actual_values == exp_value:
                report.append((key, "일치", actual_values, exp_value))
                logger.info(f"일치: {key} = {exp_value}")
            else:
                report.append((key, "불일치", actual_values, exp_value))
                logger.warning(f"불일치: {key} - 현재: {actual_values}, 기대: {exp_value}")
    
    # 요약 통계
    total = len(report)
    matched = sum(1 for item in report if item[1] == "일치")
    logger.info(f"비교 완료: 총 {total}개 중 {matched}개 일치 ({matched/total*100:.1f}%)")
    
    return report

def get_cli_commands_from_config(yaml_path: str) -> dict:
    """
    새로운 구조에서 CLI 명령어들을 추출하는 함수
    향후 CLI 기능 구현 시 사용
    """
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"CLI 명령어 추출 실패: {e}")
        return {}
    
    if 'parameters' not in config:
        logger.warning("새로운 구조가 아니므로 CLI 명령어 정보가 없습니다.")
        return {}
    
    cli_commands = {}
    for param in config['parameters']:
        name = param['name']
        cli_commands[name] = {
            'query_command': param.get('cli_query_command', ''),
            'modify_command': param.get('cli_modify_command', ''),
            'description': param.get('description', '')
        }
    
    logger.debug(f"CLI 명령어 추출 완료: {len(cli_commands)}개")
    return cli_commands

def get_parameter_details(yaml_path: str, parameter_name: str) -> dict:
    """
    특정 파라미터의 모든 정보를 반환하는 함수
    """
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"파라미터 상세 정보 추출 실패: {e}")
        return {}
    
    if 'parameters' not in config:
        logger.warning("새로운 구조가 아니므로 상세 정보가 제한됩니다.")
        return {}
    
    for param in config['parameters']:
        if param['name'] == parameter_name:
            return param
    
    logger.warning(f"파라미터를 찾을 수 없습니다: {parameter_name}")
    return {}

def list_all_parameters(yaml_path: str) -> list:
    """
    모든 파라미터 목록을 반환하는 함수
    """
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"파라미터 목록 추출 실패: {e}")
        return []
    
    if 'parameters' not in config:
        # 기존 구조에서 파라미터 목록 추출
        if 'expected_values' in config:
            params = list(config['expected_values'].keys())
            logger.debug(f"기존 구조에서 {len(params)}개 파라미터 추출")
            return params
        return []
    
    params = [param['name'] for param in config['parameters']]
    logger.debug(f"새로운 구조에서 {len(params)}개 파라미터 추출")
    return params