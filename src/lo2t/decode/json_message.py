"""
Read a JSON message and parse it
"""

import argparse
import json
import base64
from astropy.io import fits


class JsonMessage:
    """
    Class to parse a JSON message
    """
    def __init__(self, message, verbose=False):
        self.verbose = verbose
        self.message = message
        self.record = None
        self.skymap = None

    def decode_message(self):
        # Decode message value
        self.record = json.load(self.message)
        self.message = None  # free memory

    def extract_skymap(self):
        # Extract the base64-encoded skymap
        skymap_string = self.record["event"]["skymap"]

        # Decode the Base64 string to bytes
        self.skymap = base64.b64decode(skymap_string)

    def write_skymap_to_fits(self, filename):
        # Write bytes to a FITS file
        with open(filename, "wb") as fits_file:
            fits_file.write(self.skymap)

    def get_position(self):
        pass


def json_message(message, filename):
    """
    Read a JSON message and parse it
    """
    event = JsonMessage(message)
    event.decode_message()
    event.extract_skymap()
    event.write_skymap_to_fits(filename)


def json_message_argument_parser():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-r", "--record", nargs="+", help="JSON records to parse")
    parser.add_argument("-o", "--output", nargs="+", help="Output FITS filenames")
    return parser


def main():
    args = json_message_argument_parser().parse_args()
    if len(args.record) != len(args.output):
        raise ValueError("Number of records and output files must be equal")
    for messagefile, filename in zip(args.record, args.output):
        with open(messagefile, "rb") as f:
            json_message(f, filename)

        # Open and inspect the FITS file
        with fits.open(filename) as hdul:
            hdul.info()


if __name__ == "__main__":
    main()
