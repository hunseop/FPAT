import yaml
import logging
from pathlib import Path

# 로깅 설정
logger = logging.getLogger(__name__)

def validate_yaml_structure(config: dict, yaml_path: str) -> bool:
    """
    새로운 YAML 구조의 유효성을 검증하는 함수
    """
    if 'parameters' not in config:
        logger.error(f"{yaml_path}: 새로운 구조만 지원합니다. 'parameters' 섹션이 필요합니다.")
        return False
        
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

def load_expected_config(yaml_path: str) -> dict:
    """
    새로운 구조의 설정 로딩 함수
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
    
    logger.info(f"새로운 YAML 구조 로드 완료: {len(config['parameters'])}개 파라미터")
    return config

def get_prefix_map(config: dict) -> dict:
    """새로운 구조에서 prefix_map 생성"""
    prefix_map = {}
    for param in config['parameters']:
        if 'output_prefix' in param:
            prefix_map[param['output_prefix']] = param['name']
    return prefix_map

def get_expected_values(config: dict) -> dict:
    """새로운 구조에서 expected_values 추출"""
    expected_values = {}
    for param in config['parameters']:
        expected_values[param['name']] = param['expected_value']
    return expected_values

def get_command_map(config: dict) -> dict:
    """새로운 구조에서 command_map 생성 - 중복 api_command 처리 개선"""
    command_map = {}
    commands_seen = set()
    duplicate_commands = []
    
    for param in config['parameters']:
        api_cmd = param['api_command']
        
        # 중복 명령어 감지 및 로깅
        if api_cmd in commands_seen:
            duplicate_commands.append({
                'command': api_cmd,
                'parameter': param['name']
            })
            logger.info(f"중복 API 명령어 감지 - 재사용: {api_cmd} (파라미터: {param['name']})")
            continue
        
        # API 명령어에서 실제 설명 부분 추출
        if ' - ' in api_cmd:
            description, actual_cmd = api_cmd.split(' - ', 1)
            command_map[description.strip()] = actual_cmd.strip()
            logger.debug(f"명령어 등록: {description.strip()} -> {actual_cmd.strip()}")
        else:
            command_map[api_cmd] = api_cmd
            logger.debug(f"명령어 등록: {api_cmd}")
        
        commands_seen.add(api_cmd)
    
    # 중복 명령어 통계 로깅
    if duplicate_commands:
        logger.info(f"중복 제거 완료: {len(duplicate_commands)}개 중복 명령어 발견")
        for dup in duplicate_commands:
            logger.debug(f"  - {dup['command']} (파라미터: {dup['parameter']})")
    else:
        logger.debug("중복된 API 명령어 없음")
    
    logger.info(f"총 {len(command_map)}개의 고유 명령어 등록 완료")
    return command_map

def get_command_prefix_map(config: dict) -> dict:
    """새로운 구조에서 command_prefix_map 생성 - 중복 처리 개선"""
    command_prefix_map = {}
    
    for param in config['parameters']:
        api_cmd = param['api_command']
        
        # API 명령어에서 설명 부분만 추출
        if ' - ' in api_cmd:
            description = api_cmd.split(' - ', 1)[0].strip()
        else:
            description = api_cmd
            
        # 명령어별 prefix 리스트 관리
        if description not in command_prefix_map:
            command_prefix_map[description] = []
            logger.debug(f"새 명령어 그룹 생성: {description}")
        
        # prefix 중복 체크
        output_prefix = param['output_prefix']
        if output_prefix not in command_prefix_map[description]:
            command_prefix_map[description].append(output_prefix)
            logger.debug(f"prefix 등록: {description} -> {output_prefix}")
        else:
            logger.warning(f"중복 prefix 발견: {description} -> {output_prefix}")
    
    # 통계 로깅
    total_prefixes = sum(len(prefixes) for prefixes in command_prefix_map.values())
    logger.info(f"명령어-prefix 매핑 완료: {len(command_prefix_map)}개 명령어, {total_prefixes}개 prefix")
    
    return command_prefix_map

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

def compare_with_expected(parsed: dict, expected: dict, failed_keys: set, yaml_path: str = None) -> list:
    """
    개선된 비교 함수 - 새로운 6개 컬럼 구조로 리포트 생성
    컬럼: 항목, 현재값, 기대값, 상태, 확인 방법, 변경 방법
    """
    report = []
    
    # CLI 명령어 정보 가져오기
    cli_commands = {}
    if yaml_path:
        try:
            cli_commands = get_cli_commands_from_config(yaml_path)
        except Exception as e:
            logger.warning(f"CLI 명령어 정보 로드 실패: {e}")
    
    for key, exp_value in expected.items():
        exp_value = str(exp_value)
        actual_values = parsed.get(key)
        
        # CLI 명령어 정보 가져오기
        cli_info = cli_commands.get(key, {})
        query_cmd = cli_info.get('query_command', '')
        modify_cmd = cli_info.get('modify_command', '')

        # 1. 명령어 자체 실패
        if key in failed_keys:
            report.append((key, "없음", exp_value, "명령어 실패", query_cmd, modify_cmd))
            logger.warning(f"명령어 실패: {key}")
            continue
        
        # 2. 응답에서 값을 찾을 수 없음
        if actual_values is None:
            report.append((key, "없음", exp_value, "값 없음", query_cmd, modify_cmd))
            logger.warning(f"값 없음: {key}")
            continue
        
        # 3. 값 비교
        if isinstance(actual_values, list):
            current_value = ", ".join(actual_values)
            if all(v == exp_value for v in actual_values):
                report.append((key, current_value, exp_value, "일치", query_cmd, modify_cmd))
                logger.info(f"일치: {key} = {exp_value}")
            else:
                report.append((key, current_value, exp_value, "불일치", query_cmd, modify_cmd))
                logger.warning(f"불일치: {key} - 현재: {actual_values}, 기대: {exp_value}")
        else:
            actual_values = str(actual_values)
            if actual_values == exp_value:
                report.append((key, actual_values, exp_value, "일치", query_cmd, modify_cmd))
                logger.info(f"일치: {key} = {exp_value}")
            else:
                report.append((key, actual_values, exp_value, "불일치", query_cmd, modify_cmd))
                logger.warning(f"불일치: {key} - 현재: {actual_values}, 기대: {exp_value}")
    
    # 요약 통계 (상태는 4번째 컬럼)
    total = len(report)
    matched = sum(1 for item in report if item[3] == "일치")
    logger.info(f"비교 완료: 총 {total}개 중 {matched}개 일치 ({matched/total*100:.1f}%)")
    
    return report

def get_cli_commands_from_config(yaml_path: str) -> dict:
    """
    새로운 구조에서 CLI 명령어들을 추출하는 함수
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
        logger.error("새로운 구조만 지원합니다.")
        return []
    
    params = [param['name'] for param in config['parameters']]
    logger.debug(f"새로운 구조에서 {len(params)}개 파라미터 추출")
    return params

def validate_duplicate_commands(yaml_path: str) -> dict:
    """
    YAML 설정에서 중복된 api_command를 검증하고 리포트하는 함수
    
    Returns:
        dict: {
            'has_duplicates': bool,
            'total_commands': int,
            'unique_commands': int,
            'duplicate_groups': list,
            'report': str
        }
    """
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"YAML 파일 읽기 실패: {e}")
        return {'error': str(e)}
    
    if 'parameters' not in config:
        return {'error': 'parameters 섹션이 없습니다.'}
    
    # api_command별 파라미터 그룹핑
    command_groups = {}
    for param in config['parameters']:
        api_cmd = param['api_command']
        if api_cmd not in command_groups:
            command_groups[api_cmd] = []
        command_groups[api_cmd].append({
            'name': param['name'],
            'description': param.get('description', ''),
            'output_prefix': param['output_prefix']
        })
    
    # 중복 분석
    duplicate_groups = []
    for api_cmd, params in command_groups.items():
        if len(params) > 1:
            duplicate_groups.append({
                'command': api_cmd,
                'count': len(params),
                'parameters': params
            })
    
    # 리포트 생성
    total_commands = len(config['parameters'])
    unique_commands = len(command_groups)
    has_duplicates = len(duplicate_groups) > 0
    
    report_lines = [
        f"=== API 명령어 중복 검증 리포트 ===",
        f"총 파라미터 수: {total_commands}",
        f"고유 명령어 수: {unique_commands}",
        f"중복 그룹 수: {len(duplicate_groups)}",
        ""
    ]
    
    if has_duplicates:
        report_lines.append("❌ 중복된 API 명령어 발견:")
        for group in duplicate_groups:
            report_lines.append(f"\n🔄 명령어: {group['command']}")
            report_lines.append(f"   사용 횟수: {group['count']}회")
            for param in group['parameters']:
                report_lines.append(f"   - {param['name']}: {param['description']}")
                report_lines.append(f"     prefix: {param['output_prefix']}")
        
        report_lines.append("\n💡 해결 방안:")
        report_lines.append("1. 중복된 명령어를 한 번만 실행하도록 최적화됨")
        report_lines.append("2. 여러 output_prefix로 응답을 파싱하여 각 파라미터 추출")
        report_lines.append("3. 성능 향상: API 호출 횟수 감소")
    else:
        report_lines.append("✅ 중복된 API 명령어 없음 - 최적화된 상태")
    
    return {
        'has_duplicates': has_duplicates,
        'total_commands': total_commands,
        'unique_commands': unique_commands,
        'duplicate_groups': duplicate_groups,
        'report': '\n'.join(report_lines)
    }