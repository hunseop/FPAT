from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
from pathlib import Path
import sys

if getattr(sys, 'frozen', False):
    base_dir = Path(sys.executable).parent
else:
    base_dir = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(base_dir))

from fpat.firewall_module import FirewallCollectorFactory
from .parser import (
    load_expected_config,
    parse_command_output,
    compare_with_expected,
    get_cli_commands_from_config,
    get_parameter_details,
    list_all_parameters,
    get_prefix_map,
    get_expected_values,
    get_command_map,
    get_command_prefix_map,
    validate_duplicate_commands
)
from .reporter import save_report_to_excel, save_text_summary

app = FastAPI(title="Palo Alto Parameter Checker API")

class FirewallCredentials(BaseModel):
    hostname: str
    username: str
    password: str
    save_text: bool = False
    verbose: bool = False

class ParameterCheckResponse(BaseModel):
    total_parameters: int
    matched_parameters: int
    success_rate: float
    report_file: str
    text_summary_file: Optional[str] = None
    details: List[Dict[str, Any]]

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
    """방화벽 컬렉터 생성"""
    try:
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
        from fpat.firewall_module.paloalto import paloalto_module
        return paloalto_module.PaloAltoAPI(hostname, username, password)

def run_firewall_commands(collector, command_map) -> dict:
    """방화벽 명령어 실행"""
    logger = logging.getLogger(__name__)
    outputs = {}

    for description, command in command_map.items():
        logger.info(f"{description} 명령어 실행 중...")
        
        if description == "show config running match rematch":
            try:
                if hasattr(collector, 'show_config_running_match_rematch'):
                    text = collector.show_config_running_match_rematch()
                else:
                    text = collector.run_command(command)
                outputs[description] = (text, True)
                logger.debug(f"{description} 성공")
            except Exception as e:
                logger.error(f"{description} 실패: {e}")
                outputs[description] = ("", False)
        else:
            try:
                result = collector.run_command(command)
                outputs[description] = (result, True)
                logger.debug(f"{description} 성공")
            except Exception as e:
                logger.error(f"{description} 실패: {e}")
                outputs[description] = ("", False)
    
    return outputs

@app.post("/check-parameters", response_model=ParameterCheckResponse)
async def check_parameters(credentials: FirewallCredentials):
    """파라미터 점검 API 엔드포인트"""
    setup_logging(credentials.verbose)
    logger = logging.getLogger(__name__)
    
    yaml_path = base_dir / "parameters.yaml"
    
    try:
        # 설정 로드 - 새로운 구조만 지원
        logger.info("설정 파일 로딩 중...")
        config = load_expected_config(yaml_path)
        
        # 새로운 구조에서 필요한 정보 추출
        prefix_map = get_prefix_map(config)
        expected_values = get_expected_values(config)
        command_prefix_map = get_command_prefix_map(config)
        command_map = get_command_map(config)
        
        # 방화벽 연결
        collector = create_firewall_collector(
            credentials.hostname,
            credentials.username,
            credentials.password
        )

        # 명령어 실행
        all_outputs = run_firewall_commands(collector, command_map)

        # 결과 파싱
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
        report = compare_with_expected(parsed, expected_values, failed_keys, str(yaml_path))
        
        # 파일 저장
        from datetime import datetime
        today = datetime.now().date()
        output_file = str(base_dir / f"{today}_parameter_check_result_{credentials.hostname}.xlsx")
        
        save_report_to_excel(report, output_file, credentials.hostname, str(yaml_path))
        
        # 텍스트 요약 저장 (옵션)
        text_file = None
        if credentials.save_text:
            text_file = save_text_summary(report, credentials.hostname, str(base_dir))

        # 응답 생성
        total = len(report)
        matched = sum(1 for item in report if item[1] == "일치")
        
        return ParameterCheckResponse(
            total_parameters=total,
            matched_parameters=matched,
            success_rate=(matched/total*100 if total > 0 else 0),
            report_file=output_file,
            text_summary_file=text_file,
            details=report
        )

    except Exception as e:
        logger.error(f"점검 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/parameters")
async def get_parameters():
    """파라미터 목록 조회 API 엔드포인트"""
    yaml_path = base_dir / "parameters.yaml"
    try:
        params = list_all_parameters(yaml_path)
        return {"parameters": params}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/parameter/{param_name}")
async def get_parameter_detail(param_name: str):
    """파라미터 상세 정보 조회 API 엔드포인트"""
    yaml_path = base_dir / "parameters.yaml"
    try:
        details = get_parameter_details(yaml_path, param_name)
        if not details:
            raise HTTPException(status_code=404, detail="Parameter not found")
        return details
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/validate-duplicates")
async def validate_duplicates():
    """중복된 API 명령어 검증 API 엔드포인트"""
    yaml_path = base_dir / "parameters.yaml"
    try:
        result = validate_duplicate_commands(yaml_path)
        if 'error' in result:
            raise HTTPException(status_code=400, detail=result['error'])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 