import logging

logger = logging.getLogger("anamnesis")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s | %(name)s | %(message)s"))
    logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def run_server():
    from .server import mcp
    mcp.run()
