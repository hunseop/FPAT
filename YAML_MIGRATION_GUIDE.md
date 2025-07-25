# YAML 구조 마이그레이션 가이드

## 📋 개요
기존의 복잡한 4개 섹션 구조를 단순한 1개 섹션 구조로 개선하여 유지보수성과 확장성을 향상시킵니다.

## 🔄 구조 비교

### 기존 구조 (복잡)
```yaml
prefix_map:
  "CTD mode is:": "ctd_mode"
  "Rematch:": "rematch"

expected_values:
  "ctd_mode": "disabled"
  "rematch": "disabled"

command_prefix_map:
  "show system setting ctd mode":
    - "CTD mode is:"
  "show config running match rematch":
    - "Rematch:"

command_map:
  "show system setting ctd mode": "show system setting ctd mode"
  "show config running match rematch": "show config running match rematch"
```

### 새로운 구조 (단순)
```yaml
parameters:
  - name: "ctd_mode"
    description: "Content-ID 확인 모드 설정"
    expected_value: "disabled"
    api_command: "show system setting ctd mode"
    cli_query_command: "show system setting | match ctd"
    cli_modify_command: "set system setting ctd-mode disabled"
    output_prefix: "CTD mode is:"
    
  - name: "rematch"
    description: "애플리케이션 재매칭 설정"
    expected_value: "disabled"
    api_command: "show config running match rematch"
    cli_query_command: "show running application setting | match rematch"
    cli_modify_command: "set application setting rematch disabled"
    output_prefix: "Rematch:"
```

## 🎯 개선 효과

### 1. 복잡성 감소
- **기존**: 4개 섹션에 정보 분산
- **개선**: 1개 섹션에 모든 정보 집중

### 2. 중복 제거
- **기존**: 명령어 정보가 여러 곳에 중복
- **개선**: 각 파라미터당 1번만 정의

### 3. 확장성 향상
- **추가**: CLI 조회/수정 명령어 컬럼
- **추가**: 설명(description) 필드
- **향후**: 추가 메타데이터 확장 용이

### 4. 가독성 향상
- 파라미터별로 모든 정보가 함께 위치
- 논리적 그룹핑으로 이해하기 쉬움

## 🔧 마이그레이션 방법

### 1단계: 어댑터 구현 (완료)
- `parser.py`에 `_convert_new_to_old_structure()` 함수 추가
- 기존 로직 100% 보존
- 신구 구조 모두 지원

### 2단계: 새 구조로 변환
```bash
# 기존 YAML 백업
cp parameters.yaml parameters_old.yaml

# 새 구조로 작성
cp parameters_new_structure_example.yaml parameters.yaml
```

### 3단계: 테스트
```bash
# 기존과 동일한 결과 확인
python -m fpat.paloalto_parameter_checker.main --hostname <IP> --username <USER> --password <PASS>
```

## 🆕 새로운 기능 활용

### CLI 명령어 조회
```python
from fpat.paloalto_parameter_checker.parser import get_cli_commands_from_config

cli_commands = get_cli_commands_from_config("parameters.yaml")
print(cli_commands['ctd_mode']['query_command'])  # "show system setting | match ctd"
print(cli_commands['ctd_mode']['modify_command']) # "set system setting ctd-mode disabled"
```

### 파라미터 상세 정보
```python
from fpat.paloalto_parameter_checker.parser import get_parameter_details

details = get_parameter_details("parameters.yaml", "ctd_mode")
print(details['description'])  # "Content-ID 확인 모드 설정"
```

### 전체 파라미터 목록
```python
from fpat.paloalto_parameter_checker.parser import list_all_parameters

params = list_all_parameters("parameters.yaml")
print(params)  # ['ctd_mode', 'rematch', 'session_timeout', 'log_level']
```

## ⚠️ 주의사항

### 1. 로직 보존
- 기존 파싱 로직이 **완전히 동일하게** 작동함
- API 응답 처리 방식 변경 없음
- 어댑터를 통해 투명한 변환

### 2. 호환성
- 기존 구조 YAML도 계속 작동
- 점진적 마이그레이션 가능
- 롤백 시 기존 구조로 복원 가능

### 3. 확장성
- 새 필드 추가 시 기존 코드 영향 없음
- 선택적 필드 사용 가능
- 향후 기능 확장 용이

## 📝 필드 설명

| 필드명 | 필수 | 설명 |
|--------|------|------|
| `name` | ✅ | 파라미터 고유 식별자 |
| `expected_value` | ✅ | 기대하는 설정값 |
| `api_command` | ✅ | API로 조회할 명령어 |
| `output_prefix` | ✅ | 출력에서 찾을 접두사 |
| `description` | ❌ | 파라미터 설명 |
| `cli_query_command` | ❌ | CLI 조회 명령어 |
| `cli_modify_command` | ❌ | CLI 수정 명령어 |

## 🚀 마이그레이션 완료 후

1. **기존 로직**: 완전히 동일하게 작동
2. **새로운 기능**: CLI 명령어 정보 활용 가능
3. **유지보수**: 파라미터 추가/수정이 간단해짐
4. **확장성**: 향후 기능 확장이 용이해짐

---

**결론**: 이 마이그레이션은 기존 기능을 100% 보존하면서도 구조를 단순화하고 새로운 기능을 추가할 수 있는 완전한 하위 호환성을 제공합니다.