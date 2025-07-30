from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import os
from datetime import datetime
import logging

from ssh_connector import PaloAltoSSHConnector
from parameter_checker import ParameterChecker
from report_generator import ReportGenerator

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 글로벌 변수
parameter_checker = None
report_generator = None

@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')

@app.route('/api/connect', methods=['POST'])
def connect():
    """SSH 연결 설정"""
    global parameter_checker, report_generator
    
    try:
        data = request.get_json()
        host = data.get('host')
        username = data.get('username')
        password = data.get('password')
        port = data.get('port', 22)
        
        if not all([host, username, password]):
            return jsonify({'error': '호스트, 사용자명, 비밀번호는 필수입니다.'}), 400
        
        # SSH 연결 테스트
        ssh_connector = PaloAltoSSHConnector(host, username, password, port)
        connection_result = ssh_connector.connect()
        
        if not connection_result['success']:
            return jsonify({'error': f'SSH 연결 실패: {connection_result["error"]}'}), 400
        
        # Parameter Checker 초기화
        parameter_checker = ParameterChecker(ssh_connector)
        report_generator = ReportGenerator()
        
        ssh_connector.disconnect()
        
        return jsonify({
            'success': True,
            'message': 'SSH 연결이 성공했습니다.',
            'connection_info': {
                'host': host,
                'username': username,
                'port': port,
                'connected_at': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"연결 오류: {str(e)}")
        return jsonify({'error': f'연결 오류: {str(e)}'}), 500

@app.route('/api/parameters', methods=['GET'])
def get_parameters():
    """설정 가능한 매개변수 목록 조회"""
    try:
        if not parameter_checker:
            return jsonify({'error': 'SSH 연결이 설정되지 않았습니다.'}), 400
        
        parameters = parameter_checker.get_available_parameters()
        return jsonify({'parameters': parameters})
        
    except Exception as e:
        logger.error(f"매개변수 조회 오류: {str(e)}")
        return jsonify({'error': f'매개변수 조회 오류: {str(e)}'}), 500

@app.route('/api/check', methods=['POST'])
def check_parameters():
    """매개변수 점검 실행"""
    global parameter_checker
    
    try:
        if not parameter_checker:
            return jsonify({'error': 'SSH 연결이 설정되지 않았습니다.'}), 400
        
        data = request.get_json()
        selected_parameters = data.get('parameters', [])
        
        if not selected_parameters:
            return jsonify({'error': '점검할 매개변수를 선택해주세요.'}), 400
        
        # 매개변수 점검 실행
        results = parameter_checker.check_parameters(selected_parameters)
        
        return jsonify({
            'success': True,
            'results': results,
            'checked_at': datetime.now().isoformat(),
            'total_count': len(results),
            'pass_count': len([r for r in results if r['status'] == 'pass']),
            'fail_count': len([r for r in results if r['status'] == 'fail']),
            'error_count': len([r for r in results if r['status'] == 'error'])
        })
        
    except Exception as e:
        logger.error(f"매개변수 점검 오류: {str(e)}")
        return jsonify({'error': f'매개변수 점검 오류: {str(e)}'}), 500

@app.route('/api/report/generate', methods=['POST'])
def generate_report():
    """리포트 생성"""
    try:
        if not report_generator:
            return jsonify({'error': 'SSH 연결이 설정되지 않았습니다.'}), 400
        
        data = request.get_json()
        results = data.get('results', [])
        report_format = data.get('format', 'html')  # html, pdf, excel
        
        if not results:
            return jsonify({'error': '리포트 생성할 데이터가 없습니다.'}), 400
        
        # 리포트 생성
        report_info = report_generator.generate_report(results, report_format)
        
        return jsonify({
            'success': True,
            'report_info': report_info,
            'download_url': f'/api/report/download/{report_info["filename"]}'
        })
        
    except Exception as e:
        logger.error(f"리포트 생성 오류: {str(e)}")
        return jsonify({'error': f'리포트 생성 오류: {str(e)}'}), 500

@app.route('/api/report/download/<filename>')
def download_report(filename):
    """리포트 다운로드"""
    try:
        reports_dir = os.path.join(os.path.dirname(__file__), 'reports')
        return send_from_directory(reports_dir, filename, as_attachment=True)
        
    except Exception as e:
        logger.error(f"리포트 다운로드 오류: {str(e)}")
        return jsonify({'error': f'리포트 다운로드 오류: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """서비스 상태 확인"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '요청한 리소스를 찾을 수 없습니다.'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': '내부 서버 오류가 발생했습니다.'}), 500

if __name__ == '__main__':
    # 필요한 디렉토리 생성
    os.makedirs('reports', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    app.run(debug=True, host='0.0.0.0', port=5000)