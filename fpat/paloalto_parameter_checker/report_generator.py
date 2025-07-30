import os
import json
import logging
import csv
from datetime import datetime
from typing import Dict, List, Any, Optional
from jinja2 import Template

logger = logging.getLogger(__name__)

class ReportGenerator:
    """리포트 생성 클래스"""
    
    def __init__(self):
        self.reports_dir = os.path.join(os.path.dirname(__file__), 'reports')
        os.makedirs(self.reports_dir, exist_ok=True)
        
        # 상태 매핑
        self.status_mapping = {
            'pass': '정상',
            'fail': '비정상',
            'error': '오류',
            'unknown': '알 수 없음'
        }
        
        # 상태별 색상
        self.status_colors = {
            'pass': '#28a745',  # 녹색
            'fail': '#dc3545',  # 빨간색
            'error': '#ffc107', # 노란색
            'unknown': '#6c757d' # 회색
        }
    
    def generate_report(self, results: List[Dict[str, Any]], report_format: str = 'html') -> Dict[str, Any]:
        """리포트 생성"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if report_format.lower() == 'html':
                return self._generate_html_report(results, timestamp)
            elif report_format.lower() == 'csv':
                return self._generate_csv_report(results, timestamp)
            elif report_format.lower() == 'json':
                return self._generate_json_report(results, timestamp)
            else:
                raise ValueError(f"지원하지 않는 리포트 형식: {report_format}")
                
        except Exception as e:
            logger.error(f"리포트 생성 오류: {str(e)}")
            raise
    
    def _generate_html_report(self, results: List[Dict[str, Any]], timestamp: str) -> Dict[str, Any]:
        """HTML 리포트 생성"""
        filename = f"paloalto_parameter_report_{timestamp}.html"
        filepath = os.path.join(self.reports_dir, filename)
        
        # 통계 계산
        stats = self._calculate_stats(results)
        
        # HTML 템플릿
        html_template = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Palo Alto Networks 보안 매개변수 점검 보고서</title>
    <style>
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 28px;
            font-weight: 300;
        }
        .header .timestamp {
            margin-top: 10px;
            opacity: 0.9;
            font-size: 14px;
        }
        .stats {
            display: flex;
            padding: 20px;
            background-color: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
        }
        .stat-card {
            flex: 1;
            text-align: center;
            padding: 15px;
            margin: 0 10px;
            background-color: white;
            border-radius: 6px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .stat-number {
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .stat-label {
            color: #6c757d;
            font-size: 12px;
            text-transform: uppercase;
        }
        .pass { color: #28a745; }
        .fail { color: #dc3545; }
        .error { color: #ffc107; }
        .total { color: #007bff; }
        
        .content {
            padding: 20px;
        }
        .table-container {
            overflow-x: auto;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }
        th {
            background-color: #f8f9fa;
            font-weight: 600;
            color: #495057;
            position: sticky;
            top: 0;
        }
        tr:hover {
            background-color: #f8f9fa;
        }
        .status-badge {
            padding: 4px 8px;
            border-radius: 4px;
            color: white;
            font-size: 12px;
            font-weight: bold;
            text-transform: uppercase;
        }
        .command-cell {
            font-family: 'Courier New', monospace;
            font-size: 12px;
            background-color: #f8f9fa;
            border-radius: 3px;
            padding: 8px;
            max-width: 300px;
            word-break: break-all;
        }
        .description-cell {
            max-width: 200px;
        }
        .footer {
            text-align: center;
            padding: 20px;
            color: #6c757d;
            font-size: 12px;
            border-top: 1px solid #dee2e6;
            background-color: #f8f9fa;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Palo Alto Networks 보안 매개변수 점검 보고서</h1>
            <div class="timestamp">{{ report_time }}</div>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number total">{{ stats.total_count }}</div>
                <div class="stat-label">전체 항목</div>
            </div>
            <div class="stat-card">
                <div class="stat-number pass">{{ stats.pass_count }}</div>
                <div class="stat-label">정상</div>
            </div>
            <div class="stat-card">
                <div class="stat-number fail">{{ stats.fail_count }}</div>
                <div class="stat-label">비정상</div>
            </div>
            <div class="stat-card">
                <div class="stat-number error">{{ stats.error_count }}</div>
                <div class="stat-label">오류</div>
            </div>
        </div>
        
        <div class="content">
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>항목</th>
                            <th>설명</th>
                            <th>기대값</th>
                            <th>현재값</th>
                            <th>상태</th>
                            <th>확인방법</th>
                            <th>변경방법</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for result in results %}
                        <tr>
                            <td><strong>{{ result.name }}</strong></td>
                            <td class="description-cell">{{ result.description }}</td>
                            <td>{{ result.expected_value if result.expected_value else '-' }}</td>
                            <td>{{ result.current_value if result.current_value else '-' }}</td>
                            <td>
                                <span class="status-badge" style="background-color: {{ status_colors[result.status] }};">
                                    {{ status_mapping[result.status] }}
                                </span>
                            </td>
                            <td class="command-cell">{{ result.query_command }}</td>
                            <td class="command-cell">{{ result.modify_command }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="footer">
            <p>이 보고서는 자동으로 생성되었습니다. | 생성 시간: {{ report_time }}</p>
        </div>
    </div>
</body>
</html>
        """
        
        # 템플릿 렌더링
        template = Template(html_template)
        html_content = template.render(
            results=results,
            stats=stats,
            status_mapping=self.status_mapping,
            status_colors=self.status_colors,
            report_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        
        # 파일 저장
        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(html_content)
        
        logger.info(f"HTML 리포트 생성 완료: {filename}")
        
        return {
            'filename': filename,
            'filepath': filepath,
            'format': 'html',
            'size': len(html_content),
            'stats': stats
        }
    
    def _generate_csv_report(self, results: List[Dict[str, Any]], timestamp: str) -> Dict[str, Any]:
        """CSV 리포트 생성"""
        filename = f"paloalto_parameter_report_{timestamp}.csv"
        filepath = os.path.join(self.reports_dir, filename)
        
        # 통계 계산
        stats = self._calculate_stats(results)
        
        # CSV 헤더
        headers = [
            '항목', '설명', '기대값', '현재값', '상태', 
            '확인방법', '변경방법', '점검시간'
        ]
        
        # CSV 파일로 저장
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            
            # 헤더 작성
            writer.writerow(headers)
            
            # 데이터 작성
            for result in results:
                writer.writerow([
                    result.get('name', ''),
                    result.get('description', ''),
                    str(result.get('expected_value', '')),
                    str(result.get('current_value', '')),
                    self.status_mapping.get(result.get('status', 'unknown'), '알 수 없음'),
                    result.get('query_command', ''),
                    result.get('modify_command', ''),
                    result.get('checked_at', '')
                ])
        
        logger.info(f"CSV 리포트 생성 완료: {filename}")
        
        return {
            'filename': filename,
            'filepath': filepath,
            'format': 'csv',
            'stats': stats
        }
    
    def _generate_json_report(self, results: List[Dict[str, Any]], timestamp: str) -> Dict[str, Any]:
        """JSON 리포트 생성"""
        filename = f"paloalto_parameter_report_{timestamp}.json"
        filepath = os.path.join(self.reports_dir, filename)
        
        # 통계 계산
        stats = self._calculate_stats(results)
        
        # JSON 데이터 구성
        report_data = {
            'report_info': {
                'title': 'Palo Alto Networks 보안 매개변수 점검 보고서',
                'generated_at': datetime.now().isoformat(),
                'format': 'json',
                'version': '1.0'
            },
            'statistics': stats,
            'results': results
        }
        
        # 파일 저장
        with open(filepath, 'w', encoding='utf-8') as file:
            json.dump(report_data, file, ensure_ascii=False, indent=2)
        
        logger.info(f"JSON 리포트 생성 완료: {filename}")
        
        return {
            'filename': filename,
            'filepath': filepath,
            'format': 'json',
            'stats': stats
        }
    
    def _calculate_stats(self, results: List[Dict[str, Any]]) -> Dict[str, int]:
        """통계 계산"""
        total_count = len(results)
        pass_count = len([r for r in results if r.get('status') == 'pass'])
        fail_count = len([r for r in results if r.get('status') == 'fail'])
        error_count = len([r for r in results if r.get('status') == 'error'])
        
        return {
            'total_count': total_count,
            'pass_count': pass_count,
            'fail_count': fail_count,
            'error_count': error_count,
            'pass_rate': round((pass_count / total_count * 100) if total_count > 0 else 0, 1)
        }
    
    def get_report_list(self) -> List[Dict[str, Any]]:
        """생성된 리포트 목록 조회"""
        reports = []
        
        try:
            for filename in os.listdir(self.reports_dir):
                if filename.startswith('paloalto_parameter_report_'):
                    filepath = os.path.join(self.reports_dir, filename)
                    stat = os.stat(filepath)
                    
                    reports.append({
                        'filename': filename,
                        'size': stat.st_size,
                        'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        'format': filename.split('.')[-1].lower()
                    })
            
            # 생성 시간 역순 정렬
            reports.sort(key=lambda x: x['created_at'], reverse=True)
            
        except Exception as e:
            logger.error(f"리포트 목록 조회 오류: {str(e)}")
        
        return reports
    
    def delete_report(self, filename: str) -> bool:
        """리포트 파일 삭제"""
        try:
            filepath = os.path.join(self.reports_dir, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"리포트 삭제 완료: {filename}")
                return True
            else:
                logger.warning(f"리포트 파일을 찾을 수 없음: {filename}")
                return False
                
        except Exception as e:
            logger.error(f"리포트 삭제 오류: {str(e)}")
            return False