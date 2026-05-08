# LanternAI

AI Agent용 경량 트레이서 — **토큰 수 · 구간 실행시간 · 로그** 3가지 핵심 기능

```bash
pip install git+https://github.com/woozoolinux/LanternAI.git
```

---

## 빠른 시작

```python
from lanternai import trace

@trace("llm_call")
def call_llm(prompt: str) -> str:
    # LLM 호출 코드
    return response

result = call_llm("안녕하세요")
# [lanternai] 10:23:41 INFO ▶ [llm_call] 시작 | trace_id=a1b2c3d4 | input_tokens≈12
# [lanternai] 10:23:42 INFO ✓ [llm_call] 완료 | 1.234s | 토큰: in=12 out=48 total=60
```

---

## 설치

### 기본 (콘솔 로그만)
```bash
pip install git+https://github.com/woozoolinux/LanternAI.git
```

### 정확한 토큰 계산 포함
```bash
pip install "git+https://github.com/woozoolinux/LanternAI.git#egg=lanternai[tokens]"
```

### 웹 대시보드 서버 포함
```bash
pip install "git+https://github.com/woozoolinux/LanternAI.git#egg=lanternai[all]"
```

---

## 사용법

### 1. 데코레이터 방식 (권장)

```python
from lanternai import trace

# 기본
@trace("llm_call")
def call_llm(prompt: str) -> str:
    return llm.invoke(prompt)

# 태그 추가
@trace(name="web_search", tags=["tool", "search"])
def search_web(query: str) -> list:
    return search_api.search(query)

# 함수명 자동 사용
@trace
def process_result(data: dict) -> str:
    return format(data)
```

### 2. 컨텍스트 매니저 방식

```python
from lanternai import TracerClient

with TracerClient("data_processing", tags=["etl"]) as t:
    result = heavy_computation()
    t.set_output(result)
```

### 3. LangGraph 노드에 적용

```python
from lanternai import trace

@trace("agent_node")
def agent_node(state: dict) -> dict:
    response = llm.invoke(state["messages"])
    return {"messages": state["messages"] + [response]}
```

---

## 웹 대시보드

### 서버 시작

```bash
pip install "git+https://github.com/woozoolinux/LanternAI.git#egg=lanternai[all]"
cd server/
python server.py
# ✓ LanternAI 서버 시작 | http://0.0.0.0:8765
```

### 에이전트 연결

```python
from lanternai import trace, set_endpoint

set_endpoint("http://localhost:8765")

@trace("my_agent")
def my_agent(prompt: str) -> str:
    ...
```

또는 환경변수:
```bash
export MYTRACER_ENDPOINT=http://localhost:8765
```

### 대시보드 열기

`dashboard/index.html` 을 브라우저에서 열고 서버 주소 `http://localhost:8765` 입력

---

## 환경변수

| 변수 | 설명 |
|------|------|
| `MYTRACER_ENDPOINT` | 서버 주소 (예: `http://localhost:8765`) |
| `MYTRACER_API_KEY` | API 키 (선택) |

---

## 프로젝트 구조

```
LanternAI/
├── lanternai/           # pip install 패키지
│   ├── __init__.py
│   ├── tracer.py        # @trace 데코레이터, TracerClient
│   └── context.py       # 멀티노드 트레이스 ID 공유
├── server/
│   └── server.py        # FastAPI 수집 서버 (SQLite)
├── dashboard/
│   └── index.html       # 웹 모니터링 대시보드
├── pyproject.toml
└── .gitignore
```

---

MIT License
