"""
Processor for Einstein probe messages
"""

from .base import JsonProcessor


class EinsteinprobeProcessor(JsonProcessor):
    """
    Processor for Einstein probe messages
    """
    provided_formats = [
        "gcn.notices.einstein_probe.wxt.alert",
    ]

    def __init__(self, message, verbose=False):
        super().__init__(message, verbose=verbose)

    def parse_notice(self):
        pass
