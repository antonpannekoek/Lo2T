"""
Base classes for processing GCN notices
"""
import argparse
import json
import base64
from astropy.io import fits

registered_gcn_processors = {}


def _get_processor_factory(format):
    if isinstance(format, str):
        if format not in registered_gcn_processors:
            raise ValueError("Unknown GCN notice format: %s" % format)
        return registered_gcn_processors[format]
    return format


def add_gcn_processor(processor_class):
    """
    Register a new GCN processor class, so that the `read_gcn_notice` function
    can find it.

    Do not call this directly, instead use the `GcnNoticeProcessor.register`
    method.
    """
    for cls in processor_class.provided_formats:
        registered_gcn_processors[cls] = processor_class
    return processor_class


class GcnNoticeProcessor:
    """
    Base class for processing GCN notices

    All classes that process GCN notices must inherit from this class.

    Every subclass must implement the `process` method, and must support the
    `message` argument and `verbose` keyword argument.

    Arguments:
    message (str): The GCN notice to be processed.
    verbose (bool): Whether to print verbose output.

    Attributes:
    message: The GCN notice to be processed.
    verbose: Whether to print verbose output.
    """
    def __init__(self, message, verbose=False):
        self.message = message
        self.verbose = verbose

    def process(self):
        """
        Process the GCN notice, extracting the information encoded in it.
        """
        raise NotImplementedError

    @classmethod
    def register(cls):
        """
        Register the class so that the `read_gcn_notice` function can find it.
        """
        add_gcn_processor(cls)


class JsonProcessor(GcnNoticeProcessor):
    """
    Class to parse a JSON message

    Arguments:
    message (str): The JSON GCN message to be processed
    verbose (bool): Whether to print verbose output

    Attributes:
    message (str): The JSON GCN message to be processed
    verbose (bool): Whether to print verbose output
    record (dict): The parsed JSON message
    skymap (bytes): The Base64-encoded skymap
    """
    def __init__(self, message, verbose=False):
        super().__init__(message, verbose)
        self.record = None
        self.skymap = None

    def process(self):
        """
        Process the JSON message
        """
        self.decode_message()
        self.extract_skymap()

    def decode_message(self):
        """
        Decode the JSON message
        """
        self.record = json.load(self.message)
        self.message = None  # free memory

    def get_position(self):
        pass


def read_gcn_notice(message, verbose=False):
    """
    Read a message and process it
    """
    processor_factory = _get_processor_factory(message.topic())
    notice = GcnNoticeProcessor(message, verbose=verbose)
    notice.process()
    return notice


def gcn_notice_argument_parser():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-r", "--record", nargs="+", help="GCN message to parse")
    return parser


def main():
    args = gcn_notice_argument_parser().parse_args()
    if len(args.record) != len(args.output):
        raise ValueError("Number of records and output files must be equal")
    for messagefile, filename in zip(args.record, args.output):
        with open(messagefile, "rb") as f:
            read_gcn_notice(f, filename)


if __name__ == "__main__":
    main()
