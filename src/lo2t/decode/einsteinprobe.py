"""
Processor for Einstein probe messages
"""

from .base import JsonProcessor


class EinsteinprobeProcessor(JsonProcessor):
    """
    Processor for Einstein probe messages
    """
    provided_formats = ["einstein"]

    def __init__(self, message, verbose=False):
        super().__init__(message, verbose=verbose)
