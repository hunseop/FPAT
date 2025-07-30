import yaml
import re
import os
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from ssh_connector import PaloAltoSSHConnector

logger = logging.getLogger(__name__)

class ParameterChecker:
    """Palo Alto 매개변수 점검을 수행하는 클래스"""
    
    def __init__(self, ssh_connector: PaloAltoSSHConnector):
        self.ssh_connector = ssh_connector
        self.parameters_config = None
        self.ssh_config = None
        self.report_config = None
        self._load_config()
    
    def _load_config(self):
        """parameters.yaml 설정 파일 로드"""
        try:
            config_path = os.path.join(os.path.dirname(__file__), 'parameters.yaml')
            
            with open(config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
            
            self.parameters_config = config.get('parameters', [])
            self.ssh_config = config.get('ssh_config', {})
            self.report_config = config.get('report_config', {})
            
            logger.info(f"설정 파일 로드 완료: {len(self.parameters_config)}개 매개변수")
            
        except FileNotFoundError:
            logger.error("parameters.yaml 파일을 찾을 수 없습니다")
            raise
        except yaml.YAMLError as e:
            logger.error(f"YAML 파싱 오류: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"설정 파일 로드 오류: {str(e)}")
            raise
    
    def get_available_parameters(self) -> List[Dict[str, Any]]:
        """사용 가능한 매개변수 목록 반환"""
        parameters = []
        
        for param in self.parameters_config:
            parameters.append({
                'name': param.get('name'),
                'description': param.get('description'),
                'expected_value': param.get('expected_value'),
                'result_type': param.get('result_type', 'single'),
                'multi_result': param.get('multi_result', False)
            })
        
        return parameters
    
    def check_parameters(self, parameter_names: List[str]) -> List[Dict[str, Any]]:
        """선택된 매개변수들을 점검"""
        results = []
        
        # SSH 연결 확인
        if not self.ssh_connector.is_connected():
            reconnect_result = self.ssh_connector.reconnect()
            if not reconnect_result['success']:
                logger.error("SSH 재연결 실패")
                return self._create_error_results(parameter_names, "SSH 연결 실패")
        
        for param_name in parameter_names:
            try:
                param_config = self._find_parameter_config(param_name)
                if not param_config:
                    results.append(self._create_error_result(param_name, "매개변수 설정을 찾을 수 없습니다"))
                    continue
                
                result = self._check_single_parameter(param_config)
                results.append(result)
                
            except Exception as e:
                logger.error(f"매개변수 '{param_name}' 점검 오류: {str(e)}")
                results.append(self._create_error_result(param_name, str(e)))
        
        return results
    
    def _find_parameter_config(self, param_name: str) -> Optional[Dict[str, Any]]:
        """매개변수 설정 찾기"""
        for param in self.parameters_config:
            if param.get('name') == param_name:
                return param
        return None
    
    def _check_single_parameter(self, param_config: Dict[str, Any]) -> Dict[str, Any]:
        """단일 매개변수 점검"""
        param_name = param_config.get('name')
        description = param_config.get('description')
        expected_value = param_config.get('expected_value')
        query_command = param_config.get('query_command')
        modify_command = param_config.get('modify_command')
        match_pattern = param_config.get('match_pattern')
        match_group = param_config.get('match_group', 1)
        separator = param_config.get('separator')
        multi_result = param_config.get('multi_result', False)
        result_type = param_config.get('result_type', 'single')
        
        logger.info(f"매개변수 점검 시작: {param_name}")
        
        try:
            # SSH 명령어 실행
            command_result = self.ssh_connector.execute_command(query_command)
            
            if not command_result['success']:
                return self._create_error_result(
                    param_name, 
                    f"명령어 실행 실패: {command_result.get('error', 'Unknown error')}",
                    description, expected_value, query_command, modify_command
                )
            
            output = command_result['output']
            
            # 텍스트 파싱
            current_value = self._parse_output(output, match_pattern, match_group, separator, multi_result)
            
            # 결과 비교
            status = self._compare_values(expected_value, current_value, result_type)
            
            return {
                'name': param_name,
                'description': description,
                'expected_value': expected_value,
                'current_value': current_value,
                'status': status,
                'query_command': query_command,
                'modify_command': modify_command,
                'raw_output': output,
                'checked_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"매개변수 '{param_name}' 점검 중 오류: {str(e)}")
            return self._create_error_result(
                param_name, str(e), description, expected_value, query_command, modify_command
            )
    
    def _parse_output(self, output: str, pattern: str, group: int, separator: Optional[str], multi_result: bool) -> Union[str, List[str]]:
        """출력 텍스트 파싱"""
        try:
            if not pattern:
                return output.strip()
            
            # 정규식 매칭
            matches = re.finditer(pattern, output, re.MULTILINE | re.IGNORECASE)
            
            if multi_result:
                # 다중 결과 처리
                results = []
                for match in matches:
                    if group <= len(match.groups()):
                        value = match.group(group).strip()
                        
                        # 구분자로 분할
                        if separator:
                            split_values = [v.strip() for v in value.split(separator) if v.strip()]
                            results.extend(split_values)
                        else:
                            results.append(value)
                
                return results
            else:
                # 단일 결과 처리
                match = next(matches, None)
                if match and group <= len(match.groups()):
                    value = match.group(group).strip()
                    
                    # 구분자로 분할 (단일 결과지만 값 내에 구분자가 있는 경우)
                    if separator:
                        split_values = [v.strip() for v in value.split(separator) if v.strip()]
                        return split_values[0] if split_values else ""
                    
                    return value
                
                return ""
                
        except re.error as e:
            logger.error(f"정규식 오류: {str(e)}")
            return ""
        except Exception as e:
            logger.error(f"출력 파싱 오류: {str(e)}")
            return ""
    
    def _compare_values(self, expected: Any, current: Any, result_type: str) -> str:
        """기대값과 현재값 비교"""
        try:
            if result_type == 'list':
                # 리스트 비교
                if isinstance(expected, list) and isinstance(current, list):
                    # 순서 무관 비교
                    expected_set = set(str(v).lower() for v in expected)
                    current_set = set(str(v).lower() for v in current)
                    
                    if expected_set == current_set:
                        return 'pass'
                    else:
                        return 'fail'
                else:
                    # 타입이 다른 경우
                    return 'fail'
            else:
                # 단일 값 비교
                expected_str = str(expected).lower().strip() if expected is not None else ""
                current_str = str(current).lower().strip() if current is not None else ""
                
                if expected_str == current_str:
                    return 'pass'
                else:
                    return 'fail'
                    
        except Exception as e:
            logger.error(f"값 비교 오류: {str(e)}")
            return 'error'
    
    def _create_error_result(self, param_name: str, error_message: str, 
                           description: str = "", expected_value: Any = None,
                           query_command: str = "", modify_command: str = "") -> Dict[str, Any]:
        """오류 결과 생성"""
        return {
            'name': param_name,
            'description': description,
            'expected_value': expected_value,
            'current_value': f"오류: {error_message}",
            'status': 'error',
            'query_command': query_command,
            'modify_command': modify_command,
            'raw_output': '',
            'checked_at': datetime.now().isoformat(),
            'error': error_message
        }
    
    def _create_error_results(self, parameter_names: List[str], error_message: str) -> List[Dict[str, Any]]:
        """다중 오류 결과 생성"""
        return [self._create_error_result(name, error_message) for name in parameter_names]
    
    def check_single_parameter_by_name(self, param_name: str) -> Dict[str, Any]:
        """이름으로 단일 매개변수 점검"""
        param_config = self._find_parameter_config(param_name)
        if not param_config:
            return self._create_error_result(param_name, "매개변수 설정을 찾을 수 없습니다")
        
        return self._check_single_parameter(param_config)
    
    def get_parameter_config(self, param_name: str) -> Optional[Dict[str, Any]]:
        """매개변수 설정 조회"""
        return self._find_parameter_config(param_name)
    
    def reload_config(self):
        """설정 파일 다시 로드"""
        self._load_config()
        logger.info("설정 파일이 다시 로드되었습니다")