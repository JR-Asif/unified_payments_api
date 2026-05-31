import logging
import os
import sys
import contextvars
import logging_loki

LOKI_URL = os.getenv("LOKI_URL", "http://loki:3100/loki/api/v1/push")

customer_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("customer_id", default="-")
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class ContextFilter(logging.Filter):
    """Attach the current request_id and customer_id to every log record."""
    def filter(self, record: logging.LogRecord) -> bool:
        record.customer_id = customer_id_ctx.get()
        record.request_id = request_id_ctx.get()
        return True


logger = logging.getLogger("unified-payments-api")
logger.setLevel(logging.INFO)

if not logger.handlers:
    logger.addFilter(ContextFilter())

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] [req=%(request_id)s cust=%(customer_id)s] "
        "%(name)s: %(message)s"
    ))
    logger.addHandler(console_handler)

    loki_handler = logging_loki.LokiHandler(
        url=LOKI_URL,
        tags={"service": "unified-payments-api"},
        version="1",
    )
    loki_handler.setFormatter(logging.Formatter(
        "[req=%(request_id)s cust=%(customer_id)s] %(message)s"
    ))
    logger.addHandler(loki_handler)

logger.propagate = False
