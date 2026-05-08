"""
LanternAI - Lightweight AI Agent Tracer
AI 에이전트의 토큰 수, 구간 실행시간, 로그를 추적하고 웹 대시보드로 모니터링

사용법:
    from lanternai import trace, set_endpoint

    set_endpoint("http://localhost:8765")  # 웹 대시보드 사용 시

    @trace("llm_call")
    def call_llm(prompt: str) -> str:
        ...
"""

from .tracer import trace, TracerClient, set_endpoint, set_api_key
from .context import TraceContext

__version__ = "0.1.0"
__all__ = ["trace", "TracerClient", "set_endpoint", "set_api_key", "TraceContext"]
