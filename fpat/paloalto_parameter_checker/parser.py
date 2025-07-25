import yaml

def load_expected_config(yaml_path: str) -> dict:
    with open(yaml_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 새로운 구조인지 확인
    if 'parameters' in config:
        return _convert_new_to_old_structure(config)
    else:
        # 기존 구조 그대로 반환
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
    
    return old_structure

def parse_command_output(output: str, prefix_map: dict) -> dict:
    result = {}
    lines = output

    for line in lines:
        line = line.strip().rstrip(',')
        for prefix, key in prefix_map.items():
            if line.startswith(prefix):
                parts = line.split(": ", 1)
                if len(parts) == 2:
                    value = parts[1].strip()
                    result.setdefault(key, []).append(value)
    
    return result

def compare_with_expected(parsed: dict, expected: dict, failed_keys: set) -> list:
    report = []
    for key, exp_value in expected.items():
        exp_value = str(exp_value)
        actual_values = parsed.get(key)

        # 1. 명령어 자체 실패
        if key in failed_keys:
            report.append((key, "명령어 실패", "없음", exp_value))
            continue
        
        if actual_values is None:
            report.append((key, "없음", "없음", exp_value))
            continue
        
        if isinstance(actual_values, list):
            if all(v == exp_value for v in actual_values):
                report.append((key, f"일치", ", ".join(actual_values), exp_value))
            else:
                report.append((key, f"불일치", ", ".join(actual_values), exp_value))
        else:
            actual_values = str(actual_values)
            if actual_values == exp_value:
                report.append((key, f"일치", actual_values, exp_value))
            else:
                report.append((key, f"불일치", actual_values, exp_value))
    
    return report

def get_cli_commands_from_config(yaml_path: str) -> dict:
    """
    새로운 구조에서 CLI 명령어들을 추출하는 함수
    향후 CLI 기능 구현 시 사용
    """
    with open(yaml_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    if 'parameters' not in config:
        return {}
    
    cli_commands = {}
    for param in config['parameters']:
        name = param['name']
        cli_commands[name] = {
            'query_command': param.get('cli_query_command', ''),
            'modify_command': param.get('cli_modify_command', ''),
            'description': param.get('description', '')
        }
    
    return cli_commands

def get_parameter_details(yaml_path: str, parameter_name: str) -> dict:
    """
    특정 파라미터의 모든 정보를 반환하는 함수
    """
    with open(yaml_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    if 'parameters' not in config:
        return {}
    
    for param in config['parameters']:
        if param['name'] == parameter_name:
            return param
    
    return {}

def list_all_parameters(yaml_path: str) -> list:
    """
    모든 파라미터 목록을 반환하는 함수
    """
    with open(yaml_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    if 'parameters' not in config:
        # 기존 구조에서 파라미터 목록 추출
        if 'expected_values' in config:
            return list(config['expected_values'].keys())
        return []
    
    return [param['name'] for param in config['parameters']]