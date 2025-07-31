# Palo Alto Parameter Checker - 중복 API 명령어 해결 방안

## 문제 상황

`paloalto_parameter_check` 모듈에서 `parameters.yaml`에 `api_command`가 동일해도 여러번 같은 요청을 하는 문제가 발생할 수 있습니다.

## 문제 원인

1. **중복된 API 명령어**: 여러 파라미터가 동일한 `api_command`를 사용하는 경우
2. **비효율적인 요청**: 같은 명령어를 여러 번 실행하여 성능 저하
3. **불필요한 네트워크 트래픽**: 중복 요청으로 인한 리소스 낭비

## 해결 방안

### 1. 중복 제거 로직 개선

`parser.py`의 `get_command_map()` 함수에서 중복된 `api_command`를 자동으로 감지하고 제거합니다:

```python
def get_command_map(config: dict) -> dict:
    """중복 api_command 처리 개선"""
    command_map = {}
    commands_seen = set()
    duplicate_commands = []
    
    for param in config['parameters']:
        api_cmd = param['api_command']
        
        # 중복 명령어 감지 및 로깅
        if api_cmd in commands_seen:
            duplicate_commands.append({
                'command': api_cmd,
                'parameter': param['name']
            })
            logger.info(f"중복 API 명령어 감지 - 재사용: {api_cmd}")
            continue
        
        # 고유 명령어만 등록
        command_map[api_cmd] = api_cmd
        commands_seen.add(api_cmd)
    
    return command_map
```

### 2. 중복 검증 도구

#### CLI에서 중복 검증

```bash
# 중복 명령어 검증
python main.py --check-duplicates

# 일반 실행
python main.py --hostname 192.168.1.1 --username admin --password secret
```

#### API 엔드포인트

```bash
# 중복 검증 API
GET /validate-duplicates

# 응답 예시
{
  "has_duplicates": true,
  "total_commands": 5,
  "unique_commands": 3,
  "duplicate_groups": [...]
}
```

### 3. 최적화 효과

#### Before (중복 요청)
```
1. show system setting ctd mode         # ctd_mode
2. show config running match rematch    # rematch  
3. show system setting session timeout  # session_timeout
4. show system setting ctd mode         # ctd_advanced_mode (중복!)
5. show system setting session timeout  # session_idle_timeout (중복!)
```
**총 5번의 API 호출**

#### After (중복 제거)
```
1. show system setting ctd mode         # ctd_mode + ctd_advanced_mode
2. show config running match rematch    # rematch
3. show system setting session timeout  # session_timeout + session_idle_timeout
```
**총 3번의 API 호출 (40% 감소)**

### 4. 파싱 로직 개선

하나의 명령어 결과에서 여러 파라미터를 추출하도록 `get_command_prefix_map()` 함수 개선:

```python
def get_command_prefix_map(config: dict) -> dict:
    """명령어별 여러 prefix 매핑"""
    command_prefix_map = {}
    
    for param in config['parameters']:
        api_cmd = param['api_command']
        if api_cmd not in command_prefix_map:
            command_prefix_map[api_cmd] = []
        command_prefix_map[api_cmd].append(param['output_prefix'])
    
    return command_prefix_map
```

## 사용법

### 1. 현재 설정 검증

```bash
# 독립 테스트 스크립트 실행
python3 test_duplicate_check.py
```

### 2. 중복이 있는 YAML 예시

`parameters_with_duplicates_example.yaml` 파일에서 중복 상황을 확인할 수 있습니다:

```yaml
parameters:
  - name: "ctd_mode"
    api_command: "show system setting ctd mode"
    output_prefix: "CTD mode is:"
    
  - name: "ctd_advanced_mode"  
    api_command: "show system setting ctd mode"  # 중복!
    output_prefix: "CTD advanced mode:"
```

### 3. 결과 확인

```
=== API 명령어 중복 검증 리포트 ===
총 파라미터 수: 5
고유 명령어 수: 3
중복 그룹 수: 2

❌ 중복된 API 명령어 발견:

🔄 명령어: show system setting ctd mode
   사용 횟수: 2회
   - ctd_mode: Content-ID 확인 모드 설정
   - ctd_advanced_mode: Content-ID 고급 모드 설정

💡 해결 방안:
1. 중복된 명령어를 한 번만 실행하도록 최적화됨
2. 여러 output_prefix로 응답을 파싱하여 각 파라미터 추출  
3. 성능 향상: API 호출 횟수 감소
```

## 개선 효과

1. **성능 향상**: 중복 API 호출 제거로 실행 시간 단축
2. **네트워크 최적화**: 불필요한 트래픽 감소
3. **로깅 개선**: 중복 감지 및 최적화 과정 추적
4. **유지보수성**: 중복 문제를 사전에 감지하고 해결

## 주의사항

1. **prefix 고유성**: 동일한 명령어에서 여러 값을 추출할 때 `output_prefix`가 고유해야 함
2. **결과 형식**: 명령어 결과가 예상한 형식과 일치하는지 확인 필요
3. **로그 모니터링**: 중복 제거 과정을 로그로 추적하여 예상치 못한 문제 감지

이 해결 방안으로 중복 API 명령어 문제를 효과적으로 해결하고 성능을 향상시킬 수 있습니다.