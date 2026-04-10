"""结构化日志配置"""

import logging
import sys


def setup_logging(level: str = "INFO"):
    """配置全局日志格式"""
    fmt = "%(asctime)s %(levelname)-8s [%(name)s] %(message)s"
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt,
        stream=sys.stderr,
    )
