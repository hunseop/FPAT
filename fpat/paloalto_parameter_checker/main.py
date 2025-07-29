import argparse
import sys
import os
import logging
from pathlib import Path

if getattr(sys, 'frozen', False):
    base_dir = Path(sys.executable).parent
else:
    base_dir = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(base_dir))

# 개선: 팩토리 패턴 사용으로 결합도 감소
from fpat.firewall_module import FirewallCollectorFactory
from paloalto_parameter_checker.parser import (
    load_expected_config, 
    parse_command_output, 
    compare_with_expected,
    get_cli_commands_from_config,
    get_parameter_details,
    list_all_parameters,
    get_prefix_map,
    get_expected_values,
    get_command_map,
    get_command_prefix_map
)
from paloalto_parameter_checker.reporter import save_report_to_excel, save_text_summary

def setup_logging(verbose: bool = False):
    """로깅 설정"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('parameter_checker.log', encoding='utf-8')
        ]
    )

def create_firewall_collector(hostname: str, username: str, password: str):
    """
    개선된 방화벽 컬렉터 생성 - 팩토리 패턴 사용
    """
    try:
        # 팩토리를 통한 객체 생성으로 결합도 감소
        collector = FirewallCollectorFactory.create(
            vendor="paloalto",
            hostname=hostname,
            username=username,
            password=password
        )
        return collector
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"방화벽 컬렉터 생성 실패: {e}")
        # 폴백: 직접 생성
        from firewall_module.paloalto import paloalto_module
        return paloalto_module.PaloAltoAPI(hostname, username, password)

def run_firewall_commands(collector, command_map) -> dict:
    logger = logging.getLogger(__name__)
    outputs = {}

    for description, command in command_map.items():
        logger.info(f"{description} 명령어 실행 중...")
        print(f"{description} 명령어 실행")
        
        if description == "show config running match rematch":
            try:
                # 특수 메서드 확인 후 실행
                if hasattr(collector, 'show_config_running_match_rematch'):
                    text = collector.show_config_running_match_rematch()
                else:
                    text = collector.run_command(command)
                outputs[description] = (text, True)
                logger.debug(f"{description} 성공")
            except Exception as e:
                logger.error(f"{description} 실패: {e}")
                print(f"{description} 실패:", e)
                outputs[description] = ("", False)
        else:
            try:
                result = collector.run_command(command)
                outputs[description] = (result, True)
                logger.debug(f"{description} 성공")
            except Exception as e:
                logger.error(f"{description} 실패: {e}")
                print(f"{description} 실패:", e)
                outputs[description] = ("", False)
    
    return outputs

def print_parameter_info(yaml_path):
    """새로운 YAML 구조에서 파라미터 정보를 출력하는 함수"""
    logger = logging.getLogger(__name__)
    try:
        params = list_all_parameters(yaml_path)
        print(f"\n점검 대상 파라미터 총 {len(params)}개:")
        
        for param_name in params:
            details = get_parameter_details(yaml_path, param_name)
            if details and 'description' in details:
                print(f"  • {param_name}: {details['description']}")
            else:
                print(f"  • {param_name}")
        print()
    except Exception as e:
        logger.error(f"파라미터 정보 출력 중 오류: {e}")
        print(f"파라미터 정보 출력 중 오류: {e}")

def print_cli_commands_info(yaml_path):
    """CLI 명령어 정보를 출력하는 함수"""
    logger = logging.getLogger(__name__)
    try:
        cli_commands = get_cli_commands_from_config(yaml_path)
        if cli_commands:
            print("CLI 명령어 참고 정보:")
            for param_name, commands in cli_commands.items():
                if commands['query_command'] or commands['modify_command']:
                    print(f"  • {param_name}:")
                    if commands['query_command']:
                        print(f"    조회: {commands['query_command']}")
                    if commands['modify_command']:
                        print(f"    수정: {commands['modify_command']}")
            print()
    except Exception as e:
        logger.error(f"CLI 명령어 정보 출력 중 오류: {e}")
        print(f"CLI 명령어 정보 출력 중 오류: {e}")

def main():
    parser = argparse.ArgumentParser(description="Palo Alto Parameter Checker")
    parser.add_argument("--hostname", required=True, help="방화벽 IP")
    parser.add_argument("--username", required=True, help="방화벽 접속 계정")
    parser.add_argument("--password", required=True, help="방화벽 접속 비밀번호")
    parser.add_argument("--show-info", action="store_true", help="파라미터 및 CLI 명령어 정보 표시")
    parser.add_argument("--verbose", "-v", action="store_true", help="상세 로그 출력")
    parser.add_argument("--save-text", action="store_true", help="텍스트 요약 파일도 저장")
    args = parser.parse_args()

    # 로깅 설정
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    yaml_path = base_dir / "parameters.yaml"
    
    logger.info(f"Palo Alto 파라미터 점검 시작 - 대상: {args.hostname}")
    
    # 새로운 기능: 파라미터 정보 출력
    if args.show_info:
        print_parameter_info(yaml_path)
        print_cli_commands_info(yaml_path)

    try:
        # 설정 로드 - 새로운 구조만 지원
        logger.info("설정 파일 로딩 중...")
        config = load_expected_config(yaml_path)
        
        # 새로운 구조에서 필요한 정보 추출
        prefix_map = get_prefix_map(config)
        expected_values = get_expected_values(config)
        command_prefix_map = get_command_prefix_map(config)
        command_map = get_command_map(config)
        
        logger.info(f"설정 로드 완료: {len(expected_values)}개 파라미터")

        # 방화벽 연결 - 개선된 팩토리 패턴 사용
        logger.info(f"방화벽 연결 중: {args.hostname}")
        collector = create_firewall_collector(args.hostname, args.username, args.password)

        # 명령어 실행
        logger.info("방화벽 명령어 실행 시작")
        all_outputs = run_firewall_commands(collector, command_map)

        # 결과 파싱
        logger.info("결과 파싱 중...")
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
        
        # 비교 및 리포트 생성 (yaml_path 매개변수 추가)
        logger.info("결과 비교 및 리포트 생성 중...")
        report = compare_with_expected(parsed, expected_values, failed_keys, str(yaml_path))
        
        # 파일 저장
        from datetime import datetime
        today = datetime.now().date()
        output_file = os.path.join(base_dir, f"{today}_parameter_check_result_{args.hostname}.xlsx")
        
        # 개선된 리포터 사용 (YAML 경로 전달)
        save_report_to_excel(report, output_file, args.hostname, str(yaml_path))
        
        print(f"점검 완료: {output_file} 저장됨")
        logger.info(f"엑셀 리포트 저장 완료: {output_file}")
        
        # 텍스트 요약 저장 (옵션)
        if args.save_text:
            text_file = save_text_summary(report, args.hostname, str(base_dir))
            if text_file:
                print(f"텍스트 요약: {text_file} 저장됨")
        
        # 콘솔 요약 출력 (상태 컬럼이 4번째로 변경됨)
        total = len(report)
        matched = sum(1 for item in report if item[3] == "일치")
        print(f"\n점검 요약: 총 {total}개 중 {matched}개 정상 ({matched/total*100:.1f}%)")
        
    except Exception as e:
        logger.error(f"점검 중 오류 발생: {e}")
        print(f"점검 중 오류 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()