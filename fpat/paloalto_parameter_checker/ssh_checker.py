#!/usr/bin/env python3
"""
SSH 연결 및 명령어 실행 모듈
"""

import paramiko
import time
import re
import socket
from typing import Dict, Optional

class SSHChecker:
    def __init__(self):
        self.client = None
        self.shell = None
        self.is_connected = False
        self.connection_timeout = 30
        self.command_timeout = 15  # 타임아웃 증가
        self.terminal_setup_done = False
    
    def connect(self, host: str, username: str, password: str) -> Dict:
        """SSH 연결"""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # SSH 연결
            self.client.connect(
                hostname=host,
                username=username,
                password=password,
                timeout=self.connection_timeout,
                allow_agent=False,
                look_for_keys=False
            )
            
            # Shell 채널 생성
            self.shell = self.client.invoke_shell(term='xterm', width=200, height=50)
            time.sleep(2)  # 초기 프롬프트 대기 증가
            
            # 초기 출력 읽기 (환영 메시지 등)
            self._read_until_prompt()
            
            # 터미널 설정 실행
            setup_result = self._setup_terminal()
            if not setup_result['success']:
                return {
                    'success': False,
                    'message': f'터미널 설정 실패: {setup_result["message"]}'
                }
            
            self.is_connected = True
            self.terminal_setup_done = True
            
            return {
                'success': True,
                'message': f'{host}에 성공적으로 연결됨'
            }
            
        except paramiko.AuthenticationException:
            return {
                'success': False,
                'message': '인증 실패: 사용자명 또는 비밀번호를 확인하세요'
            }
        except paramiko.SSHException as e:
            return {
                'success': False,
                'message': f'SSH 연결 오류: {str(e)}'
            }
        except OSError as e:
            return {
                'success': False,
                'message': f'네트워크 연결 실패: {str(e)}'
            }
        except socket.timeout:
            return {
                'success': False,
                'message': f'연결 타임아웃 ({self.connection_timeout}초)'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'연결 실패: {str(e)}'
            }
    
    def _setup_terminal(self) -> Dict:
        """터미널 초기 설정 (페이저 끄기, 스크립트 모드 설정)"""
        try:
            setup_commands = [
                'set cli pager off',          # 페이지 출력 제거
                'set cli scripting-mode on'   # 스크립트 모드 설정
            ]
            
            for cmd in setup_commands:
                try:
                    # 명령어 전송
                    self.shell.send(cmd + '\n')
                    time.sleep(1)
                    
                    # 출력 읽고 무시 (설정 확인 메시지)
                    output = self._read_until_prompt()
                    if output is None:
                        return {'success': False, 'message': f'터미널 설정 중 연결 오류: {cmd}'}
                        
                except Exception as e:
                    return {'success': False, 'message': f'터미널 설정 실패 ({cmd}): {str(e)}'}
            
            return {'success': True, 'message': '터미널 설정 완료'}
            
        except Exception as e:
            return {'success': False, 'message': f'터미널 설정 실패: {str(e)}'}
    
    def test_connection(self) -> Dict:
        """연결 테스트"""
        if not self.is_connected:
            return {
                'success': False,
                'message': 'SSH 연결이 되어 있지 않음'
            }
        
        # 연결 건강성 확인
        health_check = self._check_connection_health()
        if not health_check['healthy']:
            return {
                'success': False,
                'message': f'연결 상태 불량: {health_check["message"]}'
            }
        
        try:
            # 간단한 명령어로 연결 테스트
            result = self.execute_command("show system info | head -5")
            if result['success']:
                return {
                    'success': True,
                    'message': 'SSH 연결 정상'
                }
            else:
                return {
                    'success': False,
                    'message': f'연결 테스트 실패: {result["message"]}'
                }
        except Exception as e:
            return {
                'success': False,
                'message': f'연결 테스트 오류: {str(e)}'
            }
    
    def _check_connection_health(self) -> Dict:
        """연결 건강성 확인"""
        try:
            if not self.client or not self.shell:
                return {'healthy': False, 'message': '클라이언트 또는 셸이 없음'}
            
            if self.shell.closed:
                return {'healthy': False, 'message': '셸 연결이 닫힘'}
            
            # Transport 레벨 확인
            transport = self.client.get_transport()
            if not transport or not transport.is_active():
                return {'healthy': False, 'message': 'Transport 연결이 비활성화됨'}
            
            return {'healthy': True, 'message': '연결 상태 양호'}
            
        except Exception as e:
            return {'healthy': False, 'message': f'연결 상태 확인 실패: {str(e)}'}
    
    def execute_command(self, command: str) -> Dict:
        """명령어 실행"""
        if not self.is_connected or not self.shell:
            return {
                'success': False,
                'message': 'SSH 연결이 되어 있지 않음',
                'output': ''
            }
        
        try:
            # 연결 상태 확인
            if self.shell.closed:
                self.is_connected = False
                return {
                    'success': False,
                    'message': 'SSH 연결이 끊어짐',
                    'output': ''
                }
            
            # 명령어에 추가 옵션 적용 (가능한 경우)
            enhanced_command = self._enhance_command(command)
            
            # 명령어 전송
            try:
                self.shell.send(enhanced_command + '\n')
                time.sleep(0.5)  # 짧은 대기
            except OSError as e:
                return {
                    'success': False,
                    'message': f'명령어 전송 실패: {str(e)}',
                    'output': ''
                }
            
            # 출력 읽기
            raw_output = self._read_until_prompt()
            
            # 연결이 중간에 끊어졌는지 확인
            if raw_output is None:
                return {
                    'success': False,
                    'message': '명령어 출력 읽기 실패 - 연결 문제',
                    'output': ''
                }
            
            # 출력 정리
            clean_output = self._clean_command_output(raw_output, enhanced_command)
            
            return {
                'success': True,
                'message': '명령어 실행 성공',
                'output': clean_output
            }
            
        except paramiko.SSHException as e:
            self.is_connected = False
            return {
                'success': False,
                'message': f'SSH 연결 오류: {str(e)}',
                'output': ''
            }
        except socket.error as e:
            self.is_connected = False
            return {
                'success': False,
                'message': f'네트워크 오류: {str(e)}',
                'output': ''
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'명령어 실행 실패: {str(e)}',
                'output': ''
            }
    
    def _enhance_command(self, command: str) -> str:
        """명령어에 추가 옵션 적용"""
        cmd = command.strip()
        
        # 이미 파이프가 있는 명령어는 그대로 사용
        if '|' in cmd:
            return command
        
        # show 명령어에 대한 향상
        if cmd.startswith('show'):
            # Palo Alto에서는 set cli pager off가 설정되어 있으므로 
            # 추가적인 페이저 옵션은 필요하지 않음
            return command
        
        # 기타 시스템 명령어들에 대한 옵션 추가 (필요시)
        linux_commands = ['ls', 'grep', 'cat', 'tail', 'head']
        cmd_parts = cmd.split()
        if cmd_parts and cmd_parts[0] in linux_commands:
            # 색상 옵션이 없으면 추가
            if '--color' not in cmd and cmd_parts[0] in ['ls', 'grep']:
                return f"{cmd} --color=never"
        
        return command
    
    def _read_until_prompt(self) -> str:
        """프롬프트가 나올 때까지 출력 읽기 (개선된 버전)"""
        output = ""
        start_time = time.time()
        last_activity = start_time
        consecutive_empty_reads = 0
        
        while time.time() - start_time < self.command_timeout:
            try:
                # 연결 상태 확인
                if self.shell.closed:
                    return None  # 연결 끊어짐 표시
                
                if self.shell.recv_ready():
                    try:
                        chunk = self.shell.recv(4096).decode('utf-8', errors='ignore')
                        if chunk:
                            output += chunk
                            last_activity = time.time()
                            consecutive_empty_reads = 0
                            
                            # 프롬프트 감지 (마지막 라인이 프롬프트인지 확인)
                            if self._check_prompt_in_output(output):
                                break
                            
                            # --More-- 패턴 감지 및 처리
                            if self._handle_more_prompt(output):
                                continue
                        else:
                            consecutive_empty_reads += 1
                    except OSError as e:
                        # recv 오류 - 연결 문제
                        return None
                    except UnicodeDecodeError:
                        # 인코딩 오류 - 계속 진행
                        consecutive_empty_reads += 1
                        continue
                else:
                    consecutive_empty_reads += 1
                    
                    # 연속으로 빈 읽기가 많으면 프롬프트 도달 가능성 확인
                    if consecutive_empty_reads > 30:  # 3초 정도
                        if self._check_prompt_in_output(output):
                            break
                        # 너무 오래 기다렸으면 종료
                        if consecutive_empty_reads > 50:  # 5초
                            break
                
                # 적응적 sleep - 활동이 있으면 짧게, 없으면 길게
                if time.time() - last_activity < 1:
                    time.sleep(0.05)  # 활발한 출력 중
                else:
                    time.sleep(0.1)   # 출력 대기 중
                    
            except paramiko.SSHException:
                # SSH 연결 오류
                return None
            except socket.error:
                # 네트워크 오류
                return None
            except Exception as e:
                # 기타 오류 - 로깅 후 계속
                time.sleep(0.1)
                continue
        
        return output
    
    def _check_prompt_in_output(self, output: str) -> bool:
        """출력에서 프롬프트 패턴 확인"""
        if not output:
            return False
        
        # 마지막 몇 줄 확인
        lines = output.split('\n')
        for line in lines[-3:]:  # 마지막 3줄 확인
            if self._is_prompt_line(line):
                return True
        return False
    
    def _handle_more_prompt(self, output: str) -> bool:
        """--More-- 프롬프트 처리 (개선된 버전)"""
        more_patterns = [
            '--More--',
            '-- More --',
            '(more)',
            '--more--',
            '-- more --'
        ]
        
        # 출력 끝부분에서 More 패턴 찾기
        output_lower = output.lower()
        for pattern in more_patterns:
            if pattern.lower() in output_lower:
                try:
                    # 스페이스바 전송으로 계속 진행
                    self.shell.send(' ')
                    time.sleep(0.1)  # 잠시 대기
                    return True
                except Exception:
                    # 전송 실패 시 무시
                    pass
        
        return False
    
    def _is_prompt_line(self, line: str) -> bool:
        """프롬프트 라인인지 확인 (개선된 버전)"""
        if not line:
            return False
        
        # ANSI 이스케이프 코드 제거 후 확인
        clean_line = self._remove_ansi_codes(line).strip()
        
        if not clean_line:
            return False
        
        # Palo Alto 장비의 일반적인 프롬프트 패턴
        prompt_patterns = [
            r'.*[>#$]\s*$',           # 일반적인 프롬프트 (>, #, $ 로 끝남)
            r'.*@.*[>#$]\s*$',        # 사용자@호스트 형태
            r'.+>\s*$',               # > 로 끝나는 프롬프트
            r'.+#\s*$',               # # 로 끝나는 프롬프트
            r'[a-zA-Z0-9\-_.]+@[a-zA-Z0-9\-_.]+[>#$]\s*$',  # 호스트명@장비명
            r'\([a-zA-Z0-9\-_.]+\)\s*[>#$]\s*$',            # (context) 형태
        ]
        
        for pattern in prompt_patterns:
            if re.match(pattern, clean_line):
                return True
        return False
    
    def _clean_command_output(self, raw_output: str, command: str) -> str:
        """명령어 출력 정리 (포괄적 정리)"""
        if not raw_output:
            return ""
        
        # 1. ANSI 이스케이프 코드 제거
        output = self._remove_ansi_codes(raw_output)
        
        # 2. 제어 문자 정리
        output = self._remove_control_characters(output)
        
        # 3. 줄 단위로 분리
        lines = output.split('\n')
        
        # 4. 명령어 에코 제거 (첫 번째 줄에서)
        clean_command = command.strip()
        if lines and clean_command in lines[0]:
            lines = lines[1:]
        
        # 5. 프롬프트 라인들 제거 (마지막부터)
        while lines and self._is_prompt_line(lines[-1]):
            lines = lines[:-1]
        
        # 6. 빈 줄 및 불필요한 라인 정리
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            # --More-- 패턴 제거
            if '--More--' in line or '-- More --' in line:
                continue
            # 빈 줄이 아니면 추가
            if line:
                cleaned_lines.append(line)
        
        # 7. 최종 출력 구성
        return '\n'.join(cleaned_lines)
    
    def _remove_ansi_codes(self, text: str) -> str:
        """ANSI 이스케이프 코드 제거"""
        if not text:
            return text
        
        # ANSI 이스케이프 시퀀스 패턴들
        ansi_patterns = [
            r'\x1b\[[0-9;]*[A-Za-z]',      # 표준 ANSI 시퀀스
            r'\x1b\][0-9;]*\x07',          # OSC 시퀀스
            r'\x1b\[[0-9;]*[mK]',          # 색상 및 지우기
            r'\x1b\[[\d;]*[JKmsu]',        # 추가 ANSI 시퀀스
            r'\x1b[()][AB0]',              # 문자셋 시퀀스
        ]
        
        for pattern in ansi_patterns:
            text = re.sub(pattern, '', text)
        
        return text
    
    def _remove_control_characters(self, text: str) -> str:
        """제어 문자 제거"""
        if not text:
            return text
        
        # 제어 문자들 제거
        control_chars = {
            '\r': '',          # 캐리지 리턴
            '\b': '',          # 백스페이스
            '\x07': '',        # 벨
            '\x0f': '',        # Shift In
            '\x0e': '',        # Shift Out
            '\x1b': '',        # ESC (이미 ANSI에서 처리되지만 혹시 남은 것들)
        }
        
        for char, replacement in control_chars.items():
            text = text.replace(char, replacement)
        
        return text
    
    def disconnect(self):
        """SSH 연결 종료"""
        try:
            if self.shell:
                self.shell.close()
                self.shell = None
            
            if self.client:
                self.client.close()
                self.client = None
            
            self.is_connected = False
            self.terminal_setup_done = False
            
        except Exception:
            pass  # 연결 종료 시 오류 무시
    
    def __del__(self):
        """객체 소멸자 - 연결 정리"""
        self.disconnect()

class ParameterChecker:
    def __init__(self):
        self.ssh = SSHChecker()
        self.command_cache = {}  # 명령어 실행 결과 캐시
    
    def connect_to_device(self, host: str, username: str, password: str) -> Dict:
        """장비에 연결"""
        self.command_cache.clear()  # 새 연결 시 캐시 초기화
        return self.ssh.connect(host, username, password)
    
    def _execute_command_with_cache(self, command: str) -> Dict:
        """캐시를 활용한 명령어 실행"""
        if command in self.command_cache:
            return self.command_cache[command]
        
        result = self.ssh.execute_command(command)
        self.command_cache[command] = result
        return result
    
    def check_parameters(self, parameters: list) -> Dict:
        """매개변수들 점검 (명령어 캐싱 적용)"""
        if not self.ssh.is_connected:
            return {
                'success': False,
                'message': 'SSH 연결이 되어 있지 않음',
                'results': []
            }
        
        results = []
        summary = {'total': len(parameters), 'pass': 0, 'fail': 0, 'error': 0}
        
        # 1. 명령어별로 파라미터 그룹화
        command_groups = {}
        for param in parameters:
            command = param['command']
            if command not in command_groups:
                command_groups[command] = []
            command_groups[command].append(param)
        
        # 2. 각 명령어 그룹 처리
        for command, param_group in command_groups.items():
            # 명령어 한 번만 실행
            cmd_result = self._execute_command_with_cache(command)
            
            if not cmd_result['success']:
                # 명령어 실행 실패 시 그룹의 모든 파라미터를 에러로 처리
                for param in param_group:
                    result = {
                        'parameter': param['name'],
                        'expected': param['expected_value'],
                        'current': 'ERROR',
                        'status': 'ERROR',
                        'query_method': command,
                        'modify_method': param['modify_command'],
                        'error': cmd_result['message']
                    }
                    results.append(result)
                    summary['error'] += 1
            else:
                # 명령어 실행 성공 시 각 파라미터별로 패턴 매칭
                output = cmd_result['output']
                for param in param_group:
                    try:
                        current_value = self._parse_output(output, param['pattern'])
                        
                        if current_value is None:
                            result = {
                                'parameter': param['name'],
                                'expected': param['expected_value'],
                                'current': 'PARSE_ERROR',
                                'status': 'ERROR',
                                'query_method': command,
                                'modify_method': param['modify_command'],
                                'error': '출력 파싱 실패'
                            }
                            summary['error'] += 1
                        else:
                            status = 'PASS' if self._compare_values(param['expected_value'], current_value) else 'FAIL'
                            result = {
                                'parameter': param['name'],
                                'expected': param['expected_value'],
                                'current': current_value,
                                'status': status,
                                'query_method': command,
                                'modify_method': param['modify_command']
                            }
                            summary['pass' if status == 'PASS' else 'fail'] += 1
                        
                        results.append(result)
                        
                    except Exception as e:
                        result = {
                            'parameter': param['name'],
                            'expected': param['expected_value'],
                            'current': 'ERROR',
                            'status': 'ERROR',
                            'query_method': command,
                            'modify_method': param['modify_command'],
                            'error': f'점검 중 오류: {str(e)}'
                        }
                        results.append(result)
                        summary['error'] += 1
        
        return {
            'success': True,
            'results': results,
            'summary': summary
        }
    
    def _parse_output(self, output: str, pattern: str) -> Optional[str]:
        """정규식으로 출력에서 값 추출 (다중 매칭 지원)"""
        try:
            import re
            
            # 모든 매칭 찾기
            matches = re.findall(pattern, output, re.MULTILINE | re.IGNORECASE)
            
            if not matches:
                return None
            
            if len(matches) == 1:
                # 단일 매칭: 기존 방식
                return matches[0].strip()
            else:
                # 다중 매칭: 모든 값이 같은지 확인
                unique_values = list(set(match.strip() for match in matches))
                
                if len(unique_values) == 1:
                    # 모든 값이 동일: "ALL_SAME(3x true)" 형태로 반환
                    return f"ALL_SAME({len(matches)}x {unique_values[0]})"
                else:
                    # 값이 다름: "MIXED(true,false,true)" 형태로 반환
                    return f"MIXED({','.join(matches)})"
            
        except Exception:
            return None
    
    def _compare_values(self, expected: str, current: str) -> bool:
        """기대값과 현재값 비교 (다중 매칭 지원)"""
        if not current:
            return False
        
        # 대소문자 무시하고 공백 제거
        expected_clean = expected.strip().lower()
        current_clean = current.strip().lower()
        
        # 다중 매칭 결과 처리
        if current_clean.startswith('all_same('):
            # "ALL_SAME(3x true)" 형태에서 실제 값 추출
            import re
            match = re.search(r'all_same\(\d+x\s*(.+)\)', current_clean)
            if match:
                actual_value = match.group(1).strip()
                return expected_clean == actual_value
            return False
        
        elif current_clean.startswith('mixed('):
            # "MIXED(true,false,true)" 형태는 항상 실패
            return False
        
        else:
            # 일반적인 단일 값 비교
            return expected_clean == current_clean
    
    def disconnect(self):
        """연결 종료"""
        self.ssh.disconnect()