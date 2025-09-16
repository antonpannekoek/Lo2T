"""
Base classes for processing GCN notices
"""
import argparse
import json
import dateutil

from lxml import etree
import astropy.units as u

registered_gcn_processors = {}


def _get_processor_factory(message_format):
    print(message_format)
    print(registered_gcn_processors)
    print(message_format in registered_gcn_processors)
    if isinstance(message_format, str):
        if message_format not in registered_gcn_processors:
            raise ValueError("Unknown GCN notice format: %s" % message_format)
        return registered_gcn_processors[message_format]
    return message_format


def add_gcn_processor(processor_class):
    """
    Register a new GCN processor class, so that the `process_gcn_notice` function
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

    provided_formats = []

    index = None
    alert_type = None
    time = None
    position = (None, None)
    healpix_index = None
    position_err = (None, None)
    distance = (None, None)
    data = None


    def __init__(self, message, verbose=False):
        self.message = message
        self.verbose = verbose

    # def process(self):
    #     """
    #     Process the GCN notice, extracting the information encoded in it.
    #     """
    #     raise NotImplementedError

    @classmethod
    def register(cls):
        """
        Register the class so that the `process_gcn_notice` function can find it.
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
        self.message = message

    def process(self):
        """
        Process the JSON message
        """
        self.decode_message()

    def parse_notice(self):
        """
        Parse the JSON message
        """
        pass

    def decode_message(self):
        """
        Decode the JSON message
        """
        self.topic = self.message.topic()
        self.record = json.loads(self.message.value())
        # self.message = None  # free memory

    def get_position(self):
        """
        Get the position of the event
        """
        pass


class VoeventProcessor(GcnNoticeProcessor):
    """
    Class to parse a VOEvent message

    Arguments:
    message (str): The VOEvent GCN message to be processed
    verbose (bool): Whether to print verbose output

    Attributes:
    message (str): The VOEvent GCN message to be processed
    verbose (bool): Whether to print verbose output
    record (dict): The parsed VOEvent message
    """
    def __init__(self, message, verbose=False):
        super().__init__(message, verbose)
        self.record = None

    def process(self):
        """
        Process the VOEvent message
        """
        self.decode_message()

    def decode_message(self):
        """
        Decode the VOEvent message
        """
        tree = etree.parse(self.message)
        root = tree.getroot()
        self.record = root

    def get_position(self):
        # position finding logic goes here
        wherewhen = self.record.find(".//WhereWhen")
        obs_data_location = wherewhen.find(".//ObsDataLocation")
        observation_location = obs_data_location.find(".//ObservationLocation")
        astro_coords = observation_location.find(".//AstroCoords")
        position2d = astro_coords.find(".//Position2D")

        if (
            position2d.find("Name1").text == "RA"
            and position2d.find("Name2").text == "Dec"
        ):
            value2 = position2d.find("Value2")
            ra = float(value2.find("C1").text) * u.deg
            dec = float(value2.find("C2").text) * u.deg
        else:
            ra = None
            dec = None

        return ra, dec

    def get_observation_time(self):
        # observation time finding logic goes here
        wherewhen = self.record.find(".//WhereWhen")
        obs_data_location = wherewhen.find(".//ObsDataLocation")
        observation_location = obs_data_location.find(".//ObservationLocation")
        astro_coords = observation_location.find(".//AstroCoords")
        astro_time = astro_coords.find(".//Time")
        time_instant = astro_time.find(".//TimeInstant")
        self.time = dateutil.parser.parse(time_instant.find(".//ISOTime").text)
        return self.time



def process_gcn_notice(message, verbose=False):
    """
    Read a message and process it
    """
    processor_factory = _get_processor_factory(message.topic())
    print(message)
    print(processor_factory)
    notice = processor_factory(message, verbose=verbose)
    print(notice)
    print(notice.message)
    notice.process()
    notice.parse_notice()
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
            process_gcn_notice(f, filename)


if __name__ == "__main__":
    main()
