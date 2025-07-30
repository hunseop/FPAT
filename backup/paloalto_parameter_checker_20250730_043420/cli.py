import click
import requests
import json
from pathlib import Path
from typing import Optional
import sys
import uvicorn
from rich.console import Console
from rich.table import Table
from rich import print as rprint

console = Console()

@click.group()
def cli():
    """Palo Alto Parameter Checker CLI"""
    pass

@cli.command()
@click.option('--host', default='localhost', help='API 서버 호스트')
@click.option('--port', default=8000, help='API 서버 포트')
def serve(host: str, port: int):
    """API 서버 실행"""
    from .api import app
    console.print(f"[green]서버 시작: http://{host}:{port}[/green]")
    uvicorn.run(app, host=host, port=port)

@cli.command()
@click.option('--hostname', required=True, help='방화벽 IP')
@click.option('--username', required=True, help='방화벽 접속 계정')
@click.option('--password', required=True, help='방화벽 접속 비밀번호')
@click.option('--save-text', is_flag=True, help='텍스트 요약 파일도 저장')
@click.option('--verbose', '-v', is_flag=True, help='상세 로그 출력')
@click.option('--api-url', default='http://localhost:8000', help='API 서버 URL')
def check(hostname: str, username: str, password: str, save_text: bool, verbose: bool, api_url: str):
    """파라미터 점검 실행"""
    try:
        with console.status("[bold green]파라미터 점검 중..."):
            response = requests.post(
                f"{api_url}/check-parameters",
                json={
                    "hostname": hostname,
                    "username": username,
                    "password": password,
                    "save_text": save_text,
                    "verbose": verbose
                }
            )
            
            if response.status_code != 200:
                console.print(f"[red]오류 발생: {response.text}[/red]")
                return
            
            result = response.json()
            
            # 결과 테이블 생성
            table = Table(title="파라미터 점검 결과")
            table.add_column("항목", style="cyan")
            table.add_column("상태", style="magenta")
            table.add_column("현재값", style="yellow")
            table.add_column("기대값", style="green")
            
            for item in result["details"]:
                status_style = {
                    "일치": "[green]일치[/green]",
                    "불일치": "[red]불일치[/red]",
                    "값 없음": "[yellow]값 없음[/yellow]",
                    "명령어 실패": "[red]명령어 실패[/red]"
                }.get(item[1], item[1])
                
                table.add_row(item[0], status_style, str(item[2]), str(item[3]))
            
            console.print(table)
            
            # 요약 정보 출력
            console.print(f"\n[bold]📊 점검 요약[/bold]")
            console.print(f"총 파라미터: {result['total_parameters']}개")
            console.print(f"일치 항목: {result['matched_parameters']}개")
            console.print(f"성공률: {result['success_rate']:.1f}%")
            console.print(f"\n[bold]📁 저장된 파일[/bold]")
            console.print(f"엑셀 리포트: {result['report_file']}")
            if result.get('text_summary_file'):
                console.print(f"텍스트 요약: {result['text_summary_file']}")

    except Exception as e:
        console.print(f"[red]오류 발생: {e}[/red]")

@cli.command()
@click.option('--api-url', default='http://localhost:8000', help='API 서버 URL')
def list_parameters(api_url: str):
    """파라미터 목록 조회"""
    try:
        with console.status("[bold green]파라미터 목록 조회 중..."):
            response = requests.get(f"{api_url}/parameters")
            
            if response.status_code != 200:
                console.print(f"[red]오류 발생: {response.text}[/red]")
                return
            
            params = response.json()["parameters"]
            
            table = Table(title="파라미터 목록")
            table.add_column("파라미터", style="cyan")
            
            for param in params:
                table.add_row(param)
            
            console.print(table)
            console.print(f"\n총 {len(params)}개 파라미터")

    except Exception as e:
        console.print(f"[red]오류 발생: {e}[/red]")

@cli.command()
@click.argument('param_name')
@click.option('--api-url', default='http://localhost:8000', help='API 서버 URL')
def show_parameter(param_name: str, api_url: str):
    """파라미터 상세 정보 조회"""
    try:
        with console.status(f"[bold green]{param_name} 파라미터 정보 조회 중..."):
            response = requests.get(f"{api_url}/parameter/{param_name}")
            
            if response.status_code == 404:
                console.print(f"[yellow]파라미터를 찾을 수 없습니다: {param_name}[/yellow]")
                return
            elif response.status_code != 200:
                console.print(f"[red]오류 발생: {response.text}[/red]")
                return
            
            details = response.json()
            
            console.print(f"\n[bold cyan]{param_name}[/bold cyan] 파라미터 정보:")
            for key, value in details.items():
                console.print(f"[green]{key}[/green]: {value}")

    except Exception as e:
        console.print(f"[red]오류 발생: {e}[/red]")

if __name__ == '__main__':
    cli() 