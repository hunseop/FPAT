"""
CLI 명령어 실행 모듈
새로운 YAML 구조의 CLI 명령어 정보를 활용하여 SSH를 통한 CLI 명령어 실행
"""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import paramiko
from fpat.paloalto_parameter_checker.parser import get_cli_commands_from_config, get_parameter_details

logger = logging.getLogger(__name__)

class CLIExecutor:
    """
    Palo Alto 방화벽 CLI 명령어 실행 클래스
    """
    
    def __init__(self, hostname: str, username: str, password: str, port: int = 22):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.port = port
        self.ssh_client = None
        
    def connect(self) -> bool:
        """SSH 연결 설정"""
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(
                hostname=self.hostname,
                username=self.username,
                password=self.password,
                port=self.port,
                timeout=30
            )
            logger.info(f"SSH 연결 성공: {self.hostname}")
            return True
        except Exception as e:
            logger.error(f"SSH 연결 실패: {e}")
            return False
    
    def disconnect(self):
        """SSH 연결 해제"""
        if self.ssh_client:
            self.ssh_client.close()
            self.ssh_client = None
            logger.info("SSH 연결 해제")
    
    def execute_command(self, command: str, timeout: int = 30) -> Tuple[str, str, int]:
        """
        단일 CLI 명령어 실행
        
        Returns:
            Tuple[stdout, stderr, exit_code]
        """
        if not self.ssh_client:
            return "", "SSH 연결이 설정되지 않았습니다.", 1
        
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(command, timeout=timeout)
            stdout_text = stdout.read().decode('utf-8')
            stderr_text = stderr.read().decode('utf-8')
            exit_code = stdout.channel.recv_exit_status()
            
            logger.debug(f"명령어 실행: {command}")
            logger.debug(f"종료 코드: {exit_code}")
            
            return stdout_text, stderr_text, exit_code
            
        except Exception as e:
            logger.error(f"명령어 실행 실패: {command} - {e}")
            return "", str(e), 1
    
    def query_parameter(self, param_name: str, yaml_path: str) -> Dict:
        """
        특정 파라미터의 현재 값을 CLI를 통해 조회
        
        Args:
            param_name: 파라미터 이름
            yaml_path: YAML 설정 파일 경로
            
        Returns:
            Dict: 조회 결과
        """
        cli_commands = get_cli_commands_from_config(yaml_path)
        
        if param_name not in cli_commands:
            return {
                'success': False,
                'error': f'파라미터를 찾을 수 없습니다: {param_name}'
            }
        
        query_command = cli_commands[param_name]['query_command']
        if not query_command or query_command.startswith('#'):
            return {
                'success': False,
                'error': f'CLI 조회 명령어가 정의되지 않았습니다: {param_name}'
            }
        
        stdout, stderr, exit_code = self.execute_command(query_command)
        
        return {
            'success': exit_code == 0,
            'command': query_command,
            'stdout': stdout,
            'stderr': stderr,
            'exit_code': exit_code
        }
    
    def modify_parameter(self, param_name: str, yaml_path: str, confirm: bool = False) -> Dict:
        """
        특정 파라미터를 기대값으로 수정
        
        Args:
            param_name: 파라미터 이름
            yaml_path: YAML 설정 파일 경로
            confirm: 실제 실행 여부 (False면 명령어만 표시)
            
        Returns:
            Dict: 수정 결과
        """
        cli_commands = get_cli_commands_from_config(yaml_path)
        param_details = get_parameter_details(yaml_path, param_name)
        
        if param_name not in cli_commands:
            return {
                'success': False,
                'error': f'파라미터를 찾을 수 없습니다: {param_name}'
            }
        
        modify_command = cli_commands[param_name]['modify_command']
        if not modify_command or modify_command.startswith('#'):
            return {
                'success': False,
                'error': f'CLI 수정 명령어가 정의되지 않았습니다: {param_name}'
            }
        
        if not confirm:
            return {
                'success': True,
                'dry_run': True,
                'command': modify_command,
                'description': param_details.get('description', ''),
                'expected_value': param_details.get('expected_value', '')
            }
        
        # 실제 명령어 실행
        stdout, stderr, exit_code = self.execute_command(modify_command)
        
        return {
            'success': exit_code == 0,
            'dry_run': False,
            'command': modify_command,
            'stdout': stdout,
            'stderr': stderr,
            'exit_code': exit_code
        }
    
    def query_all_parameters(self, yaml_path: str) -> Dict[str, Dict]:
        """
        모든 파라미터의 현재 값을 일괄 조회
        
        Returns:
            Dict: 파라미터별 조회 결과
        """
        cli_commands = get_cli_commands_from_config(yaml_path)
        results = {}
        
        for param_name in cli_commands.keys():
            logger.info(f"파라미터 조회 중: {param_name}")
            results[param_name] = self.query_parameter(param_name, yaml_path)
        
        return results
    
    def generate_config_script(self, yaml_path: str, param_names: List[str] = None) -> str:
        """
        설정 스크립트 생성 (실행하지 않고 스크립트만 생성)
        
        Args:
            yaml_path: YAML 설정 파일 경로
            param_names: 특정 파라미터들만 포함 (None이면 전체)
            
        Returns:
            str: 생성된 스크립트 내용
        """
        cli_commands = get_cli_commands_from_config(yaml_path)
        
        if param_names:
            target_params = {k: v for k, v in cli_commands.items() if k in param_names}
        else:
            target_params = cli_commands
        
        script_lines = [
            "# Palo Alto 파라미터 자동 설정 스크립트",
            "# 이 스크립트는 자동 생성되었습니다.",
            "",
            "# Configuration mode 진입",
            "configure",
            ""
        ]
        
        for param_name, commands in target_params.items():
            modify_command = commands['modify_command']
            description = commands['description']
            
            if modify_command and not modify_command.startswith('#'):
                script_lines.extend([
                    f"# {param_name}: {description}",
                    modify_command,
                    ""
                ])
        
        script_lines.extend([
            "# 설정 커밋",
            "commit",
            "",
            "# Configuration mode 종료",
            "exit"
        ])
        
        return "\n".join(script_lines)

def create_interactive_cli_tool():
    """대화형 CLI 도구 생성"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Palo Alto CLI 명령어 실행 도구")
    parser.add_argument("--hostname", required=True, help="방화벽 IP")
    parser.add_argument("--username", required=True, help="SSH 사용자명")
    parser.add_argument("--password", required=True, help="SSH 비밀번호")
    parser.add_argument("--yaml", default="parameters.yaml", help="YAML 설정 파일")
    parser.add_argument("--action", choices=['query', 'modify', 'script'], 
                       default='query', help="실행할 작업")
    parser.add_argument("--parameter", help="특정 파라미터 지정")
    parser.add_argument("--confirm", action="store_true", help="수정 명령어 실제 실행")
    parser.add_argument("--output", help="스크립트 출력 파일")
    
    args = parser.parse_args()
    
    # 로깅 설정
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(levelname)s - %(message)s')
    
    executor = CLIExecutor(args.hostname, args.username, args.password)
    
    if args.action in ['query', 'modify']:
        if not executor.connect():
            print("❌ SSH 연결 실패")
            return 1
    
    try:
        if args.action == 'query':
            if args.parameter:
                result = executor.query_parameter(args.parameter, args.yaml)
                print(f"📋 {args.parameter} 조회 결과:")
                if result['success']:
                    print(f"✅ 성공\n{result['stdout']}")
                else:
                    print(f"❌ 실패: {result['error']}")
            else:
                results = executor.query_all_parameters(args.yaml)
                for param, result in results.items():
                    status = "✅" if result['success'] else "❌"
                    print(f"{status} {param}: {result.get('stdout', result.get('error', ''))}")
        
        elif args.action == 'modify':
            if not args.parameter:
                print("❌ --parameter 옵션이 필요합니다.")
                return 1
            
            result = executor.modify_parameter(args.parameter, args.yaml, args.confirm)
            if result['success']:
                if result.get('dry_run'):
                    print(f"🔍 {args.parameter} 수정 명령어 (미실행):")
                    print(f"명령어: {result['command']}")
                    print(f"설명: {result['description']}")
                    print("실제 실행하려면 --confirm 옵션을 추가하세요.")
                else:
                    print(f"✅ {args.parameter} 수정 완료")
            else:
                print(f"❌ 실패: {result['error']}")
        
        elif args.action == 'script':
            param_list = [args.parameter] if args.parameter else None
            script = executor.generate_config_script(args.yaml, param_list)
            
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(script)
                print(f"📝 스크립트 저장: {args.output}")
            else:
                print("📝 생성된 설정 스크립트:")
                print(script)
    
    finally:
        executor.disconnect()
    
    return 0

if __name__ == "__main__":
    exit(create_interactive_cli_tool())