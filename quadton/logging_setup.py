from __future__ import annotations

import logging
import re
import sys

_REDACT = re.compile(
    r"(?i)(token|secret|password|authorization|bearer)\s*[:=]\s*\S+"
)


class _RedactFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _REDACT.sub(r"\1=***", record.msg)
        return True


def configure(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_RedactFilter())
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s :: %(message)s")
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
