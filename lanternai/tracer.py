"""
Core tracer: 토큰 측정 + 구간 실행시간 + 로그
"""

import time
import uuid
import logging
import os
import json
import functools
from datetime import datetime
from typing import Optional, Callable, Any

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False

# 전역 설정
_endpoint: Optional[str] = None
_api_key: Optional[str] = None

logging.basicConfig(
    format="[mytracer] %(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO
)
logger = logging.getLogger("mytracer")


def set_endpoint(url: str):
    """서버 엔드포인트 설정 (웹 대시보드 사용 시)"""
    global _endpoint
    _endpoint = url


def set_api_key(key: str):
    """API 키 설정"""
    global _api_key
    _api_key = key


def _count_tokens(text: str) -> int:
    """
    토큰 수 추정 (tiktoken 없이도 동작)
    평균 4자 = 1토큰 기준 (영어), 한국어는 약 2자 = 1토큰
    """
    if not text:
        return 0
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(str(text)))
    except ImportError:
        # tiktoken 없으면 근사치 사용
        text_str = str(text)
        korean_chars = sum(1 for c in text_str if '\uac00' <= c <= '\ud7a3')
        other_chars = len(text_str) - korean_chars
        return (korean_chars // 2) + (other_chars // 4)


def _send_to_server(trace_data: dict):
    """서버로 트레이스 데이터 전송 (비동기적, 실패해도 에이전트 동작에 영향 없음)"""
    endpoint = _endpoint or os.environ.get("MYTRACER_ENDPOINT")
    if not endpoint or not _HAS_HTTPX:
        return

    api_key = _api_key or os.environ.get("MYTRACER_API_KEY", "")

    try:
        httpx.post(
            f"{endpoint}/api/traces",
            json=trace_data,
            headers={"X-API-Key": api_key},
            timeout=2.0
        )
    except Exception:
        pass  # 서버 전송 실패해도 에이전트는 계속 실행


def trace(name: str = None, tags: list = None, log_input: bool = True, log_output: bool = True):
    """
    AI 에이전트 함수 트레이싱 데코레이터
    
    사용법:
        @trace("llm_call")
        def call_llm(prompt: str) -> str:
            ...
        
        @trace(name="tool_search", tags=["search", "tool"])
        def search_web(query: str) -> str:
            ...
    
    Args:
        name: 트레이스 이름 (생략 시 함수명 사용)
        tags: 분류 태그 목록
        log_input: 입력값 로깅 여부
        log_output: 출력값 로깅 여부
    """
    def decorator(func: Callable) -> Callable:
        trace_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            trace_id = str(uuid.uuid4())[:8]
            start_time = time.perf_counter()
            timestamp = datetime.now().isoformat()

            # 입력 토큰 계산
            input_text = str(args) + str(kwargs)
            input_tokens = _count_tokens(input_text)

            logger.info(f"▶ [{trace_name}] 시작 | trace_id={trace_id} | input_tokens≈{input_tokens}")

            status = "success"
            output = None
            error_msg = None

            try:
                output = func(*args, **kwargs)
                return output
            except Exception as e:
                status = "error"
                error_msg = str(e)
                logger.error(f"✗ [{trace_name}] 에러: {e}")
                raise
            finally:
                elapsed = time.perf_counter() - start_time
                output_tokens = _count_tokens(output) if output else 0
                total_tokens = input_tokens + output_tokens

                # 콘솔 로그
                status_icon = "✓" if status == "success" else "✗"
                logger.info(
                    f"{status_icon} [{trace_name}] 완료 | "
                    f"{elapsed:.3f}s | "
                    f"토큰: in={input_tokens} out={output_tokens} total={total_tokens}"
                )

                # 서버 전송용 데이터
                trace_data = {
                    "id": trace_id,
                    "name": trace_name,
                    "timestamp": timestamp,
                    "elapsed_ms": round(elapsed * 1000, 2),
                    "status": status,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "tags": tags or [],
                    "input": str(args[0] if len(args) == 1 else args)[:500] if log_input else None,
                    "output": str(output)[:500] if log_output and output else None,
                    "error": error_msg,
                }

                _send_to_server(trace_data)

        return wrapper

    # @trace 또는 @trace() 둘 다 지원
    if callable(name):
        func = name
        name = None
        return decorator(func)

    return decorator


class TracerClient:
    """
    컨텍스트 매니저로 수동 트레이싱
    
    사용법:
        with TracerClient("my_step") as t:
            result = do_something()
            t.set_output(result)
    """

    def __init__(self, name: str, tags: list = None):
        self.name = name
        self.tags = tags or []
        self.trace_id = str(uuid.uuid4())[:8]
        self._output = None
        self._status = "success"

    def __enter__(self):
        self._start = time.perf_counter()
        self._timestamp = datetime.now().isoformat()
        logger.info(f"▶ [{self.name}] 시작 | trace_id={self.trace_id}")
        return self

    def set_output(self, output: Any):
        self._output = output

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.perf_counter() - self._start
        output_tokens = _count_tokens(self._output) if self._output else 0

        if exc_type:
            self._status = "error"
            logger.error(f"✗ [{self.name}] 에러: {exc_val}")
        else:
            logger.info(
                f"✓ [{self.name}] 완료 | "
                f"{elapsed:.3f}s | "
                f"output_tokens≈{output_tokens}"
            )

        trace_data = {
            "id": self.trace_id,
            "name": self.name,
            "timestamp": self._timestamp,
            "elapsed_ms": round(elapsed * 1000, 2),
            "status": self._status,
            "input_tokens": 0,
            "output_tokens": output_tokens,
            "total_tokens": output_tokens,
            "tags": self.tags,
            "output": str(self._output)[:500] if self._output else None,
            "error": str(exc_val) if exc_val else None,
        }
        _send_to_server(trace_data)
        return False  # 예외 re-raise
