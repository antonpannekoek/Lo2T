"""
Processor for SVOM messages
"""

from .base import JsonProcessor


class SvomProcessor(JsonProcessor):
    """
    Processor for SVOM messages
    """
    provided_formats = ["svom"]

    def __init__(self, message, verbose=False):
        super().__init__(message, verbose=verbose)
