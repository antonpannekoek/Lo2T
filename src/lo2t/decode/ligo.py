"""
Deciphers LIGO JSON events

These have the following keys:
- alert_type
- time_created
- superevent_id
- urls
- event
- external_coinc


"""

import argparse
from io import BytesIO
from pprint import pprint

from astropy.table import Table
import astropy_healpix as ah
import numpy as np

from .json_message import JsonProcessor


class LigoProcessor(JsonProcessor):
    """
    Class to parse a LIGO message

    Arguments:
    message (str): The JSON GCN message to be processed
    verbose (bool): Whether to print verbose output

    Attributes:
    message (str): The JSON GCN message to be processed
    verbose (bool): Whether to print verbose output
    record (dict): The parsed JSON message
    skymap (bytes): The Base64-encoded skymap
    position (tuple): (ra, dec)
    time (datetime): The time of the event
    distance (tuple): The mean and uncertainty of the distance to the event
    """
    provided_formats = ["igwn.gwalert"]

    def __init__(self, message, verbose=False):
        super().__init__(message, verbose=verbose)
        self.position = None
        self.time = None
        self.distance = None
        self.decode_message()
        self.parse_notice()

    def get_position(self):
        return self.position

    def get_distance(self):
        return self.distance

    def get_time(self):
        return self.time

    def parse_notice(self):
        """
        Parse a LIGO notice
        """
        # Only respond to mock events. Real events have GraceDB IDs like
        # S1234567, mock events have GraceDB IDs like M1234567.
        # NOTE NOTE NOTE replace the conditional below with this commented out
        # conditional to only parse real events.
        # if record['superevent_id'][0] != 'S':
        #    return
        if self.record["superevent_id"][0] != "M":
            return

        if self.record["alert_type"] == "RETRACTION":
            print(self.record["superevent_id"], "was retracted")
            return

        # Respond only to 'CBC' events. Change 'CBC' to 'Burst' to respond to
        # only unmodeled burst events.
        if self.record["event"]["group"] != "CBC":
            return

        # Parse sky map
        self.extract_skymap()
        # skymap_str = self.record.get("event", {}).pop("skymap")
        if self.skymap:
            # Decode, parse skymap, and print most probable sky location
            # skymap_bytes = b64decode(skymap_str)
            self.skymap = Table.read(BytesIO(self.skymap))

            level, ipix = ah.uniq_to_level_ipix(
                self.skymap[np.argmax(self.skymap["PROBDENSITY"])]["UNIQ"]
            )
            self.position = ah.healpix_to_lonlat(
                ipix, ah.level_to_nside(level), order="nested"
            )
            self.distance = (
                self.skymap.meta["DISTMEAN"],
                self.skymap.meta["DISTSTD"],
            )
            self.time = (
                self.record["event"]["time"]
            )
            if self.verbose:
                print(
                    f"Most probable sky location (RA, Dec) = "
                    f"({self.position[0].deg}, {self.position[1].deg})"
                )

                # Print some information from FITS header
                print(
                    f'Distance = {self.distance[0]} +/- {self.distance[1]}'
                )

        if self.verbose > 1:
            # Print remaining fields
            print("Record:")
            pprint(self.record)


def ligo(message, **kwargs):
    event = LigoProcessor(message, **kwargs)
    event.parse_notice()


def ligo_argument_parser():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        default=0,
        action="count",
        help="Verbosity level, repeat to increase verbosity",
    )
    parser.add_argument("-r", "--record", nargs="+", help="LIGO records to parse")
    return parser


def main():
    args = ligo_argument_parser().parse_args()
    for file in args.record:
        with open(file, "r") as f:
            ligo(f, verbose=args.verbose)


if __name__ == "__main__":
    main()
