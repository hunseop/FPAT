import yaml

def load_expected_config(yaml_path: str) -> dict:
    with open(yaml_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

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