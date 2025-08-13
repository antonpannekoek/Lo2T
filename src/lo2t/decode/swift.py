"""
Processor for Swift messages.



"""
import sys
import argparse
from .base import VoeventProcessor

class SwiftProcessor(VoeventProcessor):
    """
    Processor for Swift messages
    """
    provided_formats = ["swift"]

    def __init__(self, message, verbose=False):
        super().__init__(message, verbose=verbose)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-r", "--record", nargs="+", help="Swift records to parse")
    args = parser.parse_args()
    for messagefile in args.record:
        with open(messagefile, "rb") as f:
            processor = SwiftProcessor(f, verbose=args.verbose)
            processor.process()
            print(processor.get_position())
            print(processor.get_observation_time())


if __name__ == "__main__":
    main()
