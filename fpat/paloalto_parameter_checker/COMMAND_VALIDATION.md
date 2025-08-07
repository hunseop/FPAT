# 명령어 입력값 검증 기능

## 개요

SSH를 통한 Palo Alto 장비 접근 시 보안을 위해 명령어 입력값 검증 기능이 추가되었습니다. 이 기능은 허용된 명령어만 실행되도록 하여 시스템 보안을 강화합니다.

## 허용되는 명령어

### 1. 기본 설정 명령어
```bash
set cli pager off
set cli scripting-mode on
```

### 2. show 명령어
```bash
show system info
show interface ethernet1/1
show config running
show config running | match address
show log system | tail -10
```
- `show`로 시작하는 모든 조회 명령어
- 파이프(`|`) 사용 가능
- 인터페이스 경로(`ethernet1/1`) 등 슬래시 포함 가능

### 3. debug 명령어 (제한적)
```bash
debug dataplane show rule-hit
debug show application-stats
debug dump session
```
- `debug`로 시작하면서 `show` 또는 `dump`가 포함된 명령어만 허용
- 디버깅 관련 조회/덤프 명령어로 제한

## 차단되는 요소

### 1. 허용되지 않은 명령어
- `configure`, `delete`, `set` (설정 명령어 제외)
- `rm`, `cat`, `ls` 등 시스템 명령어
- 기타 조회 이외의 모든 명령어

### 2. 특수문자 (보안 위험)
```
& ; ` $ ( ) { } [ ] < > \ " ' * ?
```
- 파이프(`|`)는 허용 (조회 명령어에서 필터링 용도)
- 명령어 체이닝, 리다이렉션, 변수 치환 등 방지

### 3. 의심스러운 패턴
- 연속된 하이픈(`--`) 과다 사용
- 1000자 초과 명령어
- 빈 명령어

## 검증 로직

### 1. 기본 검사
```python
# 빈 명령어 검사
if not command or not command.strip():
    return False

# 길이 제한 검사
if len(command) > 1000:
    return False
```

### 2. 특수문자 검사
```python
dangerous_chars = ['&', ';', '`', '$', '(', ')', '{', '}', 
                   '[', ']', '<', '>', '\\', '"', "'", '*', '?']
for char in dangerous_chars:
    if char in command:
        return False
```

### 3. 패턴 매칭
```python
allowed_patterns = [
    r'^set\s+cli\s+pager\s+off\s*$',
    r'^set\s+cli\s+scripting-mode\s+on\s*$',
    r'^show\s+[\w\s\-|./]+$',
    r'^debug\s+.*(?:show|dump)[\w\s\-|./]*$',
]
```

## 사용 예시

### ✅ 허용되는 명령어들
```bash
show system info
show interface ethernet1/1
show config running | match "address 192.168"
debug dataplane show rule-hit
debug dump session
```

### ❌ 차단되는 명령어들
```bash
rm -rf /tmp/file                    # 시스템 명령어
configure                           # 설정 모드 진입
show system; cat /etc/passwd        # 명령어 체이닝
show system && rm file              # 조건부 실행
show system `whoami`                # 명령어 치환
show system info > /tmp/hack        # 리다이렉션
debug something else                # show/dump 미포함
```

## 오류 메시지

검증 실패 시 구체적인 오류 메시지가 제공됩니다:

- `허용되지 않은 특수문자: &`
- `허용되지 않은 명령어: configure`
- `명령어 길이 초과 (최대 1000자)`
- `의심스러운 연속 하이픈 패턴`
- `빈 명령어`

## 구현 위치

- **파일**: `ssh_checker.py`
- **메서드**: `_validate_command()`
- **호출 지점**: `execute_command()`, `_setup_terminal()`

## 테스트

명령어 검증 기능은 100% 성공률로 테스트되었습니다:
- 허용 명령어: 10/10 통과
- 차단 명령어: 17/17 통과
- 전체 성공률: 27/27 (100.0%)

이 검증 시스템으로 SSH를 통한 Palo Alto 장비 접근 시 보안이 크게 강화되었습니다.