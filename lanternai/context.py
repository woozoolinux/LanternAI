"""TraceContext - 트레이스 ID를 여러 함수에 걸쳐 공유할 때 사용"""

import contextvars

_current_trace_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_trace_id", default=None
)


class TraceContext:
    """멀티 노드 에이전트에서 동일한 트레이스 ID 공유"""

    def __init__(self, trace_id: str = None):
        import uuid
        self.trace_id = trace_id or str(uuid.uuid4())[:8]
        self._token = None

    def __enter__(self):
        self._token = _current_trace_id.set(self.trace_id)
        return self

    def __exit__(self, *args):
        _current_trace_id.reset(self._token)


def get_current_trace_id() -> str:
    return _current_trace_id.get()
