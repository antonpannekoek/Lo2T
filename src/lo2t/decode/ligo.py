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

import os
import tempfile
import datetime
import argparse
import base64
from io import BytesIO
from pprint import pprint

import requests
from astropy.table import Table
import astropy_healpix as ah
import numpy as np

from .base import JsonProcessor


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
    position_err (tuple): (ra, dec)
    time (datetime): The time of the event
    distance (tuple): The mean and uncertainty of the distance to the event
    """
    provided_formats = ["igwn.gwalert"]

    def __init__(self, message, verbose=False):
        super().__init__(message, verbose=verbose)
        self.index = None
        self.message = message
        self.position = (None, None)
        self.position_err = (None, None)
        self.time = None
        self.distance = (None, None)
        self.terrestrial_chance = None
        self.false_alarm_rate = None
        self.has_neutron_star = None
        self.has_remnant = None
        self.skymap = None
        self.decode_message()
        self.parse_notice()

    def process(self):
        """
        Processes the JSON message
        """
        self.decode_message()
        self.extract_skymap()

    def extract_skymap(self):
        """
        Extracts the base64-encoded skymap
        """
        print(f"Record keys: {self.record.keys()}")
        # print(f"Event keys: {self.record['event'].keys()}")
        try:
            skymap_str = self.record["event"]["skymap"]
        except ValueError:
            print("No skymap (ValueError)")
            return
        except TypeError:
            print("No skymap (TypeError)")
            return

        # Decode the Base64 string to bytes
        self.skymap = base64.b64decode(skymap_str)

    def write_skymap_to_fits(self, filename):
        skymap = Table.read(BytesIO(self.skymap))

        # Write bytes to a FITS file
        with open(filename, "wb") as fits_file:
            fits_file.write(skymap)

    def get_position(self):
        return self.position

    def get_distance(self):
        return self.distance

    def get_time(self):
        return self.time

    def parse_notice(self):
        """
        Parse a LIGO notice.

        See https://emfollow.docs.ligo.org/userguide/tutorial/receiving/gcn.html#receiving-and-parsing-notices
        """
        # Only respond to real events.
        # Real events have GraceDB IDs like S1234567, mock events have GraceDB
        # IDs like M1234567.
        # if self.record['superevent_id'][0] != 'S':
        #     return
        # if self.record["superevent_id"][0] != "M":
        #     return
        self.index = self.record["superevent_id"]
        self.alert_type = self.record["alert_type"]

        if self.record["alert_type"] == "RETRACTION":
            print(self.record["superevent_id"], "was retracted")
            return

        # Respond only to 'CBC' events. Change 'CBC' to 'Burst' to respond to
        # only unmodeled burst events.
        if self.record["event"]["group"] != "CBC":
            return

        # Parse time
        self.time = datetime.datetime.strptime(
            self.record["event"]["time"],
            "%Y-%m-%dT%H:%M:%S.%fZ",
        )

        # Parse sky map
        self.extract_skymap()
        # skymap_str = self.record.get("event", {}).pop("skymap")

        if self.skymap is not None:
            # Decode, parse skymap, and print most probable sky location
            # skymap_bytes = b64decode(skymap_str)
            skymap = Table.read(BytesIO(self.skymap))

            # Location with highest probability density in the skymap is chosen
            # as location
            level, ipix = ah.uniq_to_level_ipix(
                skymap[np.argmax(skymap["PROBDENSITY"])]["UNIQ"]
            )
            self.position = ah.healpix_to_lonlat(
                ipix, ah.level_to_nside(level), order="nested"
            )
            try:
                self.distance = (
                    skymap.meta["DISTMEAN"],
                    skymap.meta["DISTSTD"],
                )
            except KeyError:
                pass

            self.terrestrial_chance = self.record["event"]["classification"]["Terrestrial"]
            self.false_alarm_rate = self.record["event"]["far"]
            self.has_neutron_star = self.record["event"]["properties"]["HasNS"]
            self.has_remnant = self.record["event"]["properties"]["HasRemnant"]

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
                print("Writing skymap to FITS file")
                superevent_id = self.record["superevent_id"]
                if not os.path.exists(superevent_id):
                    os.mkdir(superevent_id)
                filename = os.path.join(superevent_id, "skymap.fits")
                self.write_skymap_to_fits(filename)

        if self.verbose > 2:
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
    parser.add_argument(
        "-t", "--test", action="store_true", 
        help="Test mode: download and parse test event"
    )
    return parser


def main():
    args = ligo_argument_parser().parse_args()
    if args.test:
        list_of_messages = [
            "https://emfollow.docs.ligo.org/userguide/_downloads/5ae1eb9a4ae5aaf3505f83b110bcb954/MS181101ab-earlywarning.json",
            "https://emfollow.docs.ligo.org/userguide/_downloads/84cc6bbbd1de21294e40f9bca4a3a3d9/MS181101ab-preliminary.json",
            "https://emfollow.docs.ligo.org/userguide/_downloads/9512c334adf9bd37b7632501a981c6e0/MS181101ab-initial.json",
            "https://emfollow.docs.ligo.org/userguide/_downloads/b5f608ad3594d33a3613776c15fef9a5/MS181101ab-update.json",
            "https://emfollow.docs.ligo.org/userguide/_downloads/9f8ecf8418fea677a04dc39811fe9943/MS181101ab-retraction.json",
            "https://emfollow.docs.ligo.org/userguide/_downloads/a8cb61f0b98aae26aecb5e5fda68a29e/MS181101ab-ext-update.json",
        ]
        # Create tempdir
        with tempfile.TemporaryDirectory() as tempdir:
            for url in list_of_messages:
                r = requests.get(url, timeout=10)
                with open(
                    os.path.join(tempdir, os.path.basename(url)),
                    "w",
                    encoding="utf-8",
                ) as f:
                    f.write(r.text)

                with open(
                    os.path.join(tempdir, os.path.basename(url)),
                    "r",
                    encoding="utf-8",
                ) as f:
                    ligo(f, verbose=args.verbose)
        return

    for file in args.record:
        with open(file, "r") as f:
            ligo(f, verbose=args.verbose)


if __name__ == "__main__":
    main()
