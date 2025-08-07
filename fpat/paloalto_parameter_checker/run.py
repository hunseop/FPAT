#!/usr/bin/env python3
"""
Palo Alto Parameter Checker 실행 스크립트
"""

if __name__ == '__main__':
    from app import app
    print("=" * 60)
    print("🛡️  Palo Alto Parameter Checker v2.0")
    print("=" * 60)
    print("📍 서버 주소: http://localhost:5012")
    print("🔗 브라우저에서 위 주소로 접속하세요")
    print("=" * 60)
    
    try:
        app.run(host='0.0.0.0', port=5012, debug=False)
    except KeyboardInterrupt:
        print("\n👋 프로그램을 종료합니다.")
    except Exception as e:
        print(f"❌ 프로그램 시작 오류: {e}")