"""
starter_kit 패키지
일반적인 RPA/자동화 테스트 관련 유틸리티를 제공합니다.
"""

from .config_example import *  # noqa
from .capture_from_cursor import *  # noqa
from .template_quality_check import *  # noqa

__all__ = [
    "config_example",
    "capture_from_cursor",
    "template_quality_check",
]
