"""
Process IceCube JSON events
"""

from .base import JsonProcessor


class IcecubeProcessor(JsonProcessor):
    """
    Processor for IceCube JSON events
    """
    def __init__(self, message, verbose=False):
        super().__init__(message, verbose=verbose)
