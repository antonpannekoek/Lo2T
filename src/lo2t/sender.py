"""
Tools for triggering LOFAR
"""
import sys
import toml
import requests
import datetime
import json

from .location import radec_to_altaz

from lofar_tmss_client.standalone_trigger_client import TMSSsession


class LofarTrigger(TMSSsession):
    """
    Class for connecting to LOFAR and submitting trigger events.
    """

    def __init__(self, settings):
        self.settings = settings
        super().__init__(
            settings["lofar"]["username"],
            settings["lofar"]["password"],
            host=settings["lofar"]["host"],
            port=settings["lofar"]["port"],
        )

    def submit_event(self, event):
        """Submits a trigger event to LOFAR
        """
        ra, dec = event.position
        cal_ra, cal_dec = event.calibrator_position

        # calculate current alt, az
        alt, az = radec_to_altaz(
            ra, dec, datetime.datetime.now(), site="LOFAR"
        )

        print(f"Position: {ra}, {dec}")
        print(f"Calibrator position: {cal_ra}, {cal_dec}")
        print(f"Altitude: {alt}")
        print(f"Azimuth: {az}")

        # submit the event to LOFAR


def main(settings=None):
    if settings is None:
        # Open settings toml file
        settings = toml.load(sys.argv[1])
    with LofarTrigger(settings) as session:
        for template in session.get_scheduling_unit_observing_strategy_templates():
            print(
                "id=%s name='%s' version=%s"
                % (template["id"], template["name"], template["version"])
            )


if __name__ == "__main__":
    main()
