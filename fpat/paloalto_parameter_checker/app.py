#!/usr/bin/env python3
"""
Palo Alto Parameter Checker - Flask 웹 애플리케이션
"""

import os
import json
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from datetime import datetime
import tempfile

from parameter_manager import ParameterManager
from ssh_checker import ParameterChecker
from report import ReportGenerator

app = Flask(__name__)
CORS(app)

# 전역 객체들
param_manager = ParameterManager()
checker = ParameterChecker()
report_generator = ReportGenerator()

@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')

# 매개변수 관리 API
@app.route('/api/parameters', methods=['GET'])
def get_parameters():
    """매개변수 목록 조회"""
    try:
        parameters = param_manager.get_all_parameters()
        return jsonify({
            'success': True,
            'parameters': parameters
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'매개변수 조회 실패: {str(e)}'
        }), 500

@app.route('/api/parameters', methods=['POST'])
def add_parameter():
    """새 매개변수 추가"""
    try:
        data = request.get_json()
        
        # 데이터 검증
        validation = param_manager.validate_parameter_data(data)
        if not validation['valid']:
            return jsonify({
                'success': False,
                'message': validation['message']
            }), 400
        
        # 매개변수 추가
        result = param_manager.add_parameter(
            name=data['name'],
            description=data['description'],
            expected_value=data['expected_value'],
            command=data['command'],
            modify_command=data['modify_command'],
            pattern=data['pattern']
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'매개변수 추가 실패: {str(e)}'
        }), 500

@app.route('/api/parameters/<int:param_id>', methods=['PUT'])
def update_parameter(param_id):
    """매개변수 수정"""
    try:
        data = request.get_json()
        
        # 데이터 검증
        validation = param_manager.validate_parameter_data(data)
        if not validation['valid']:
            return jsonify({
                'success': False,
                'message': validation['message']
            }), 400
        
        # 매개변수 수정
        result = param_manager.update_parameter(
            param_id=param_id,
            name=data['name'],
            description=data['description'],
            expected_value=data['expected_value'],
            command=data['command'],
            modify_command=data['modify_command'],
            pattern=data['pattern']
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'매개변수 수정 실패: {str(e)}'
        }), 500

@app.route('/api/parameters/<int:param_id>', methods=['DELETE'])
def delete_parameter(param_id):
    """매개변수 삭제"""
    try:
        result = param_manager.delete_parameter(param_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'매개변수 삭제 실패: {str(e)}'
        }), 500

# 설정 관리 API
@app.route('/api/export', methods=['GET'])
def export_parameters():
    """매개변수 설정 내보내기"""
    try:
        result = param_manager.export_parameters()
        
        if result['success']:
            return jsonify(result['data'])
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'내보내기 실패: {str(e)}'
        }), 500

@app.route('/api/import', methods=['POST'])
def import_parameters():
    """매개변수 설정 가져오기"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': '가져올 데이터가 없습니다'
            }), 400
        
        result = param_manager.import_parameters(data)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'가져오기 실패: {str(e)}'
        }), 500

@app.route('/api/reset', methods=['POST'])
def reset_parameters():
    """기본 매개변수로 초기화"""
    try:
        result = param_manager.reset_to_defaults()
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'초기화 실패: {str(e)}'
        }), 500

# 점검 관련 API
@app.route('/api/check', methods=['POST'])
def check_parameters():
    """매개변수 점검 실행"""
    try:
        data = request.get_json()
        
        # 필수 필드 검증
        required_fields = ['host', 'username', 'password']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'message': f'{field} 필드는 필수입니다'
                }), 400
        
        # SSH 연결
        connection_result = checker.connect_to_device(
            host=data['host'],
            username=data['username'],
            password=data['password']
        )
        
        if not connection_result['success']:
            return jsonify(connection_result), 400
        
        try:
            # 매개변수 목록 가져오기
            parameters = param_manager.get_all_parameters()
            
            if not parameters:
                return jsonify({
                    'success': False,
                    'message': '점검할 매개변수가 없습니다'
                }), 400
            
            # 매개변수 점검 실행
            check_result = checker.check_parameters(parameters)
            
            # 결과를 세션에 저장 (리포트 생성용)
            app.config['LAST_CHECK_RESULTS'] = check_result['results']
            app.config['LAST_CHECK_SUMMARY'] = check_result['summary']
            
            return jsonify(check_result)
            
        finally:
            # SSH 연결 종료
            checker.disconnect()
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'점검 실행 실패: {str(e)}'
        }), 500

# 리포트 다운로드 API
@app.route('/api/download/excel', methods=['GET'])
def download_excel_report():
    """Excel 리포트 다운로드"""
    try:
        # 마지막 점검 결과 확인
        if 'LAST_CHECK_RESULTS' not in app.config:
            return jsonify({
                'success': False,
                'message': '다운로드할 점검 결과가 없습니다. 먼저 점검을 실행하세요.'
            }), 400
        
        results = app.config['LAST_CHECK_RESULTS']
        summary = app.config['LAST_CHECK_SUMMARY']
        
        # Excel 리포트 생성
        report_result = report_generator.generate_excel_report(results, summary)
        
        if report_result['success']:
            return send_file(
                report_result['filepath'],
                as_attachment=True,
                download_name=report_result['filename'],
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        else:
            return jsonify({
                'success': False,
                'message': report_result['message']
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Excel 리포트 다운로드 실패: {str(e)}'
        }), 500


# 헬스 체크 API
@app.route('/api/health', methods=['GET'])
def health_check():
    """서버 상태 확인"""
    return jsonify({
        'success': True,
        'message': 'Palo Alto Parameter Checker 서버가 정상 동작 중입니다',
        'timestamp': datetime.now().isoformat()
    })

# 오류 핸들러
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'message': '요청한 리소스를 찾을 수 없습니다'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'message': '서버 내부 오류가 발생했습니다'
    }), 500

if __name__ == '__main__':
    # 개발 서버 실행
    print("=" * 60)
    print("🛡️  Palo Alto Parameter Checker v2.0")
    print("=" * 60)
    print("📍 서버 주소: http://localhost:5012")
    print("🔗 브라우저에서 위 주소로 접속하세요")
    print("=" * 60)
    
    try:
        # 오래된 리포트 파일 정리
        report_generator.cleanup_old_reports()
        
        app.run(host='0.0.0.0', port=5012, debug=True)
    except KeyboardInterrupt:
        print("\n👋 서버를 종료합니다.")
    except Exception as e:
        print(f"❌ 서버 시작 오류: {e}")