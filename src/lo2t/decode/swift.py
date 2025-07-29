"""
Processor for Swift messages
"""

from .base import JsonProcessor


class SwiftProcessor(JsonProcessor):
    """
    Processor for Swift messages
    """
    provided_formats = ["swift"]

    def __init__(self, message, verbose=False):
        super().__init__(message, verbose=verbose)
