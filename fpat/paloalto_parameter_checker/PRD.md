# Palo Alto Parameter Checker PRD (Product Requirements Document)

## 📋 프로젝트 개요

### 목적
Palo Alto Networks 장비의 보안 매개변수를 SSH를 통해 점검하고 결과를 리포트로 제공하는 단순한 웹 애플리케이션

### 배경
- 기존 API 방식은 일부 명령어 미지원
- 폐쇄망 환경에서 사용 필요
- 복잡한 설정 없이 바로 사용 가능해야 함

## 🎯 핵심 기능

### 1. SSH 연결
- IP, 사용자ID, 비밀번호 입력
- SSH 연결 테스트 및 상태 표시

### 2. 매개변수 점검
- 사전 정의된 명령어들을 순차 실행
- SSH 출력 결과 파싱
- 기대값과 현재값 비교

### 3. 결과 표시 및 저장
- 실시간 점검 결과 테이블 표시
- HTML/CSV 리포트 생성
- 결과 다운로드 기능

## 🖥️ UI 구성

### 메인 화면 (단일 페이지)

```
┌─────────────────────────────────────────────────────────┐
│                Palo Alto Parameter Checker              │
├─────────────────────────────────────────────────────────┤
│ 연결 정보                                                │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐        │
│ │   IP    │ │   ID    │ │   PW    │ │ 점검시작 │        │
│ └─────────┘ └─────────┘ └─────────┘ └─────────┘        │
├─────────────────────────────────────────────────────────┤
│ 점검 결과                                 ┌─────────┐    │
│ ┌─────────────────────────────────────────┐ │결과저장 │    │
│ │ 파라미터 │기대값│현재값│상태│조회방법│변경방법│ └─────────┘    │
│ ├─────────────────────────────────────────┤             │
│ │ ctd_mode │disabled│enabled│FAIL│show...│set...│             │
│ │ rematch  │yes     │yes    │PASS│show...│set...│             │
│ │ timeout  │60      │30     │FAIL│show...│set...│             │
│ └─────────────────────────────────────────┘             │
└─────────────────────────────────────────────────────────┘
```

## 🔧 기술 사양

### 기술 스택
- **백엔드**: Flask (Python)
- **프론트엔드**: HTML + Bootstrap + Vanilla JavaScript
- **SSH 라이브러리**: Paramiko
- **설정 파일**: YAML

### 파일 구조
```
paloalto_parameter_checker/
├── app.py                  # Flask 메인 앱
├── ssh_checker.py          # SSH 연결 및 명령어 실행
├── parser.py               # 출력 파싱 로직
├── report.py               # 리포트 생성
├── parameters.yaml         # 매개변수 정의
├── templates/
│   └── index.html         # 메인 UI
├── static/
│   ├── bootstrap.min.css  # 스타일
│   └── app.js            # JavaScript
└── reports/               # 생성된 리포트
```

## 📊 데이터 구조

### parameters.yaml
```yaml
parameters:
  - name: "ctd_mode"
    description: "Content-ID 확인 모드"
    expected: "disabled"
    command: "show system setting ctd mode"
    modify: "set system setting ctd-mode disabled"
    pattern: "CTD mode is: (\\w+)"
    
  - name: "session_timeout"
    description: "세션 타임아웃"
    expected: "60"
    command: "show system setting session timeout"
    modify: "set system setting session timeout 60"
    pattern: "timeout: (\\d+)"
```

### 점검 결과 데이터
```json
{
  "parameter": "ctd_mode",
  "expected": "disabled", 
  "current": "enabled",
  "status": "FAIL",
  "query_method": "show system setting ctd mode",
  "modify_method": "set system setting ctd-mode disabled"
}
```

## 🔄 프로세스 플로우

### 1. 사용자 입력
```
사용자 → IP/ID/PW 입력 → 점검시작 버튼 클릭
```

### 2. SSH 연결 및 점검
```
Flask → SSH 연결 → 명령어 실행 → 출력 파싱 → 결과 비교
```

### 3. 결과 표시
```
결과 데이터 → JSON 응답 → JavaScript → 테이블 업데이트
```

## 🎯 상세 요구사항

### SSH 처리
- **연결 타임아웃**: 30초
- **명령어 타임아웃**: 10초
- **프롬프트 감지**: `>` 또는 `#` 문자로 명령어 완료 판단
- **에러 처리**: 연결 실패, 인증 실패, 명령어 실패 시 적절한 메시지

### 출력 파싱
- **정규식 기반**: 각 매개변수별 패턴 정의
- **공백 제거**: 출력값의 앞뒤 공백 제거
- **대소문자 무시**: 비교 시 대소문자 구분 안함
- **SSH 특성 고려**: 프롬프트, 에코, 제어 문자 제거

### 상태 판정
- **PASS**: 기대값 = 현재값
- **FAIL**: 기대값 ≠ 현재값  
- **ERROR**: 명령어 실행 실패 또는 파싱 실패

### UI 동작
- **실시간 업데이트**: 점검 진행 상황 표시
- **상태 색상**: PASS(녹색), FAIL(빨간색), ERROR(주황색)
- **로딩 표시**: 점검 중 스피너 표시
- **결과 다운로드**: HTML, CSV 형식 지원

## 📝 API 설계

### 엔드포인트
```
POST /api/check          # 매개변수 점검 실행
GET  /api/download/html  # HTML 리포트 다운로드  
GET  /api/download/csv   # CSV 리포트 다운로드
```

### 요청/응답 예시
```javascript
// 점검 요청
POST /api/check
{
  "host": "192.168.1.1",
  "username": "admin", 
  "password": "password"
}

// 점검 응답
{
  "success": true,
  "results": [
    {
      "parameter": "ctd_mode",
      "expected": "disabled",
      "current": "enabled", 
      "status": "FAIL",
      "query_method": "show system setting ctd mode",
      "modify_method": "set system setting ctd-mode disabled"
    }
  ],
  "summary": {
    "total": 10,
    "pass": 7,
    "fail": 2, 
    "error": 1
  }
}
```

## 🚀 구현 우선순위

### Phase 1: 핵심 기능
1. SSH 연결 및 명령어 실행
2. 기본 출력 파싱
3. 단순 결과 표시

### Phase 2: UI 개선
1. Bootstrap 기반 반응형 UI
2. 실시간 상태 업데이트
3. 로딩 상태 표시

### Phase 3: 리포트 기능
1. HTML 리포트 생성
2. CSV 리포트 생성  
3. 다운로드 기능

## ⚡ 성능 요구사항

- **점검 시간**: 매개변수당 평균 2-3초
- **동시 연결**: 단일 세션 (순차 처리)
- **메모리 사용**: 최대 100MB
- **파일 크기**: 리포트 파일 최대 10MB

## 🔒 보안 고려사항

- SSH 비밀번호는 메모리에만 저장 (세션 종료 시 삭제)
- 입력값 검증 및 SQL 인젝션 방지
- 생성된 리포트 파일 자동 정리 (24시간 후)
- 로그에 민감정보 기록 금지

## 🎯 성공 지표

- **사용성**: 5분 이내 설치 및 사용 가능
- **안정성**: 99% 정상 점검 완료율
- **정확성**: 수동 점검 대비 100% 일치율
- **효율성**: 수동 점검 대비 80% 시간 단축

---

이 PRD를 기반으로 단순하고 실용적인 Palo Alto Parameter Checker를 구현합니다.