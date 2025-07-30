import paramiko
import time
import re
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class PaloAltoSSHConnector:
    """Palo Alto 장비에 SSH 연결을 관리하는 클래스"""
    
    def __init__(self, host: str, username: str, password: str, port: int = 22):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.ssh_client = None
        self.shell = None
        self.timeout = 30
        self.command_timeout = 10
        
    def connect(self) -> Dict[str, any]:
        """SSH 연결 수행"""
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            logger.info(f"SSH 연결 시도: {self.username}@{self.host}:{self.port}")
            
            self.ssh_client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=self.timeout,
                allow_agent=False,
                look_for_keys=False
            )
            
            # 인터랙티브 셸 시작
            self.shell = self.ssh_client.invoke_shell()
            self.shell.settimeout(self.command_timeout)
            
            # 초기 출력 읽기 및 프롬프트 대기
            time.sleep(2)
            initial_output = self._read_until_prompt()
            
            logger.info(f"SSH 연결 성공: {self.host}")
            
            return {
                'success': True,
                'message': f'SSH 연결 성공: {self.host}',
                'initial_output': initial_output
            }
            
        except paramiko.AuthenticationException:
            error_msg = "인증 실패: 사용자명 또는 비밀번호를 확인하세요"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
            
        except paramiko.SSHException as e:
            error_msg = f"SSH 연결 오류: {str(e)}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
            
        except Exception as e:
            error_msg = f"연결 오류: {str(e)}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    def disconnect(self):
        """SSH 연결 종료"""
        try:
            if self.shell:
                self.shell.close()
                self.shell = None
            
            if self.ssh_client:
                self.ssh_client.close()
                self.ssh_client = None
                
            logger.info(f"SSH 연결 종료: {self.host}")
            
        except Exception as e:
            logger.error(f"연결 종료 오류: {str(e)}")
    
    def execute_command(self, command: str) -> Dict[str, any]:
        """명령어 실행"""
        try:
            if not self.shell:
                return {
                    'success': False,
                    'error': 'SSH 연결이 설정되지 않았습니다',
                    'output': '',
                    'command': command
                }
            
            logger.info(f"명령어 실행: {command}")
            
            # 명령어 전송
            self.shell.send(command + '\n')
            time.sleep(1)  # 명령어 실행 대기시간 증가
            
            # 출력 읽기
            output = self._read_until_prompt()
            
            # 명령어 에코 제거
            lines = output.split('\n')
            if lines and command.strip() in lines[0]:
                lines = lines[1:]
            
            # 프롬프트 제거 (간단한 방식)
            if lines and ('>' in lines[-1] or '#' in lines[-1] or '$' in lines[-1]):
                lines = lines[:-1]
            
            clean_output = '\n'.join(lines).strip()
            
            logger.debug(f"명령어 출력 ({len(clean_output)} chars): {clean_output[:200]}...")
            
            return {
                'success': True,
                'output': clean_output,
                'command': command,
                'raw_output': output
            }
            
        except Exception as e:
            error_msg = f"명령어 실행 오류: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'output': '',
                'command': command
            }
    
    def _read_until_prompt(self) -> str:
        """프롬프트가 나타날 때까지 출력 읽기 (단순화된 버전)"""
        output = ""
        max_wait = 30  # 최대 30초 대기
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                if self.shell.recv_ready():
                    chunk = self.shell.recv(4096).decode('utf-8', errors='ignore')
                    output += chunk
                    
                    # 간단한 프롬프트 확인 (> # $ 로 끝나는 라인)
                    lines = output.split('\n')
                    if lines:
                        last_line = lines[-1].strip()
                        if last_line.endswith('>') or last_line.endswith('#') or last_line.endswith('$'):
                            break
                else:
                    time.sleep(0.1)
                    
            except Exception as e:
                logger.warning(f"출력 읽기 중 오류: {str(e)}")
                break
        
        return output
    
    def test_connection(self) -> Dict[str, any]:
        """연결 테스트"""
        if not self.shell:
            return {'success': False, 'error': 'SSH 연결이 없습니다'}
        
        return self.execute_command('show system info | head -5')
    
    def is_connected(self) -> bool:
        """연결 상태 확인"""
        try:
            if not self.ssh_client or not self.shell:
                return False
            
            # 간단한 명령어로 연결 상태 테스트
            result = self.execute_command('show system info | head -1')
            return result['success']
            
        except Exception:
            return False
    
    def reconnect(self) -> Dict[str, any]:
        """재연결"""
        logger.info("SSH 재연결 시도...")
        self.disconnect()
        time.sleep(2)
        return self.connect()
    
    def __enter__(self):
        """Context manager 진입"""
        connection_result = self.connect()
        if not connection_result['success']:
            raise Exception(f"SSH 연결 실패: {connection_result['error']}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 종료"""
        self.disconnect()