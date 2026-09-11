"""Token Meter — tracks target tokens, judge tokens, and API call counts per evaluation metric run."""
import threading

class TokenMeter:
    def __init__(self):
        self._lock = threading.Lock()
        self.reset()

    def reset(self):
        with self._lock:
            self.target_tokens = 0
            self.judge_tokens = 0
            self.judge_calls = 0

    def add_target_usage(self, usage: dict | None):
        if not usage:
            return
        with self._lock:
            p = usage.get("prompt_tokens", 0)
            c = usage.get("completion_tokens", 0)
            self.target_tokens += (p + c)

    def add_judge_usage(self, prompt_tokens: int = 0, completion_tokens: int = 0):
        with self._lock:
            self.judge_tokens += (prompt_tokens + completion_tokens)
            self.judge_calls += 1

    def total_tokens(self) -> int:
        with self._lock:
            return self.target_tokens + self.judge_tokens

    def summary_str(self) -> str:
        with self._lock:
            total = self.target_tokens + self.judge_tokens
            return f"{total} tokens · target {self.target_tokens} · judge {self.judge_tokens} · {self.judge_calls} calls"

    def to_dict(self) -> dict:
        with self._lock:
            total = self.target_tokens + self.judge_tokens
            return {
                "target_tokens": self.target_tokens,
                "judge_tokens": self.judge_tokens,
                "total_tokens": total,
                "judge_calls": self.judge_calls,
                "formatted": f"{total} tokens · target {self.target_tokens} · judge {self.judge_tokens} · {self.judge_calls} calls"
            }

token_meter = TokenMeter()
