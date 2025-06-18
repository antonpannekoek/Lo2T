"""
Functions for decoding GCN notices
"""

from .base import registered_gcn_processors
from .base import read_gcn_notice
from .ligo import LigoProcessor
from .icecube import IcecubeProcessor


LigoProcessor.register()
IcecubeProcessor.register()


__all__ = ["read_gcn_notice"]
