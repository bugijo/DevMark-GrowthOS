import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock


@dataclass
class _AttemptWindow:
    failures: int
    started_at: float


class InMemoryLoginRateLimiter:
    """Limita falhas de login dentro de um único processo.

    O lock torna o armazenamento seguro entre threads, mas cada réplica mantém
    sua própria memória. Produção com múltiplas réplicas deve substituir este
    adaptador por um store compartilhado, como Redis, preservando o contrato.
    """

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._windows: dict[str, _AttemptWindow] = {}
        self._lock = Lock()

    def retry_after(self, key: str, *, attempts: int, window_seconds: int) -> int | None:
        now = self._clock()
        with self._lock:
            current = self._active_window(key, now, window_seconds)
            if current is None or current.failures < attempts:
                return None
            return max(1, math.ceil(window_seconds - (now - current.started_at)))

    def register_failure(self, key: str, *, window_seconds: int) -> None:
        now = self._clock()
        with self._lock:
            current = self._active_window(key, now, window_seconds)
            if current is None:
                self._windows[key] = _AttemptWindow(failures=1, started_at=now)
            else:
                current.failures += 1

    def clear(self, key: str) -> None:
        with self._lock:
            self._windows.pop(key, None)

    def reset(self) -> None:
        """Remove todas as janelas; destinada também ao isolamento dos testes."""
        with self._lock:
            self._windows.clear()

    def _active_window(
        self,
        key: str,
        now: float,
        window_seconds: int,
    ) -> _AttemptWindow | None:
        current = self._windows.get(key)
        if current is not None and now - current.started_at >= window_seconds:
            self._windows.pop(key, None)
            return None
        return current


login_rate_limiter = InMemoryLoginRateLimiter()


def reset_login_rate_limiter() -> None:
    login_rate_limiter.reset()
