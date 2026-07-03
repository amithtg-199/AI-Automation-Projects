"""
Adaptive rate limiter for LLM API calls.

Strategy:
  - Starts with the configured inter-request delay (GENERATION_BATCH_DELAY).
  - On a 429 / rate-limit error it doubles the delay (capped at 60 s)
    then retries up to LLM_MAX_RETRIES times.
  - On success it halves the delay back toward the baseline so paid tiers
    quickly converge to near-zero wait and free tiers self-tune.
  - All waits are logged so the pipeline log stays transparent.

Usage:
    limiter = AdaptiveRateLimiter()
    response = limiter.invoke(chain, input_vars, label="batch 3/10 test_cases")
"""

import time
import re
from scripts.config import config
from scripts.logger import get_logger

logger = get_logger(__name__)

_RETRYABLE_PATTERNS = re.compile(
    r"429|rate.?limit|too many requests|quota exceeded|resource_exhausted"
    r"|timed?\s*out|timeout|read operation timed out|connect.+timed out"
    r"|502|503|504|service.?unavailable|bad gateway",
    re.IGNORECASE,
)


class AdaptiveRateLimiter:
    def __init__(self):
        self._base_delay = config.GENERATION_BATCH_DELAY
        self._delay = self._base_delay
        self._max_delay = 60.0
        self._max_retries = config.LLM_MAX_RETRIES

    @staticmethod
    def _is_retryable_error(exc: Exception) -> bool:
        msg = str(exc)
        return bool(_RETRYABLE_PATTERNS.search(msg))

    def invoke(self, chain, input_vars: dict, *, label: str = ""):
        """
        Invoke the LangChain chain with adaptive rate-limit handling.
        Returns the raw AIMessage response.
        """
        last_exc = None
        for attempt in range(1, self._max_retries + 1):
            # Pre-request delay (skipped on first call if delay is 0)
            if self._delay > 0:
                logger.debug(f"Rate-limiter: waiting {self._delay:.1f}s before request ({label})")
                time.sleep(self._delay)

            try:
                response = chain.invoke(input_vars)
                # Success → ease the delay back toward baseline
                self._delay = max(self._base_delay, self._delay / 2)
                return response

            except Exception as exc:
                last_exc = exc
                if self._is_retryable_error(exc):
                    self._delay = min(self._delay * 2 or 1.0, self._max_delay)
                    logger.warning(
                        f"Retryable error ({label}). "
                        f"Retry {attempt}/{self._max_retries} in {self._delay:.1f}s. "
                        f"Error: {exc}"
                    )
                else:
                    # Non-retryable errors propagate immediately
                    raise

        # Exhausted retries
        raise RuntimeError(
            f"Rate limit retries exhausted after {self._max_retries} attempts ({label}). "
            f"Last error: {last_exc}"
        )
