import argparse
import sys
import os
from pathlib import Path

if getattr(sys, 'frozen', False):
    base_dir = Path(sys.executable).parent
else:
    base_dir = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(base_dir))

from firewall_module.paloalto import paloalto_module
from paloalto_parameter_checker.parser import load_expected_config, parse_command_output, compare_with_expected
from paloalto_parameter_checker.reporter import save_report_to_excel

def run_firewall_commands(collector, command_map) -> dict:
    outputs = {}

    for description, command in command_map.items():
        print(f"{description} 명령어 실행")
        if description == "show config running match rematch":
            try:
                text = collector.show_config_running_match_rematch()
                outputs[description] = (text, True)
            except Exception as e:
                print(f"{description} 실패:", e)
                outputs[description] = ("", False)
        else:
            try:
                outputs[description] = (collector.run_command(command), True)
            except Exception as e:
                print(f"{description} 실패:", e)
                outputs[description] = ("", False)
    
    return outputs

def main():
    parser = argparse.ArgumentParser(description="Palo Alto Parameter Checker")
    parser.add_argument("--hostname", required=True, help="방화벽 IP")
    parser.add_argument("--username", required=True, help="방화벽 접속 계정")
    parser.add_argument("--password", required=True, help="방화벽 접속 비밀번호")
    args = parser.parse_args()

    yaml_path = base_dir / "parameters.yaml"

    # 설정 로드
    config = load_expected_config(yaml_path)
    prefix_map = config["prefix_map"]
    expected_values = config["expected_values"]
    command_prefix_map = config["command_prefix_map"]
    command_map = config["command_map"]

    collector = paloalto_module.PaloAltoAPI(
        hostname=args.hostname,
        username=args.username,
        password=args.password
    )

    all_outputs = run_firewall_commands(collector, command_map)

    parsed = {}
    failed_keys = set()

    for cmd_name, (output, success) in all_outputs.items():
        if cmd_name == 'show system setting ctd mode' and not ':' in output[0]:
            output = [f'CTD mode is: {output[0]}']
        if success:
            partial = parse_command_output(output, prefix_map)
            for k, v in partial.items():
                parsed.setdefault(k, []).extend(v)
        else:
            for prefix in command_prefix_map.get(cmd_name, []):
                key = prefix_map.get(prefix)
                if key:
                    failed_keys.add(key)
    
    report = compare_with_expected(parsed, expected_values, failed_keys)
    from datetime import datetime
    today = datetime.now().date()
    output_file = os.path.join(base_dir, f"{today}_parameter_check_result_{args.hostname}.xlsx")
    save_report_to_excel(report, output_file, args.hostname)

    print(f"점검 완료: {output_file} 저장됨")

if __name__ == "__main__":
    main()