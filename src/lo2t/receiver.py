"""
Receive Kafka GCN messages
"""

import logging
import time
import datetime
import argparse
import tomllib
from functools import reduce
from gcn_kafka import Consumer

import astropy.units as u

from .db import Lo2tDb
from .decode import process_gcn_notice


def get_nested_value(nested_dict, keys):
    """
    Get a nested value from a nested dictionary
    """
    return reduce(lambda d, k: d[k], keys, nested_dict)


def receiver_argument_parser():
    """
    Parse command line arguments and show defaults in help
    """
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Receive Kafka GCN messages and process these",
    )
    parser.add_argument(
        "-c",
        "--configfile",
        default="config.toml",
        help="Path to configuration file",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        default=0,
        action="count",
        help="Verbosity level, repeat to increase verbosity",
    )
    parser.add_argument(
        "-t",
        "--test_message",
        default="",
        type=str,
        help="Test message to process",
    )
    return parser


class GcnNotices:
    """
    Class for receiving and keeping track of GCN notices
    """

    logger = logging.getLogger(__name__)
    consumer = None
    db = None
    config = None

    def __init__(self, configfile="config.toml", verbose=0):
        self.logger.setLevel(10 - verbose * 10)
        self.config = self.load_config(configfile)
        self.db = Lo2tDb(self.config)

    def load_config(self, configfile):
        """
        Load config file
        """
        with open(configfile, "rb") as f:
            config = tomllib.load(f)
        subscriptions = config["gcn"]["subscriptions"]
        for subscription in subscriptions:
            self.logger.info("Registered for %s notices", subscription)
        return config

    def connect(self):
        """
        Connect as a consumer
        Warning: don't share the client secret with others.
        """
        self.consumer = Consumer(
            client_id=self.config["gcn"]["credentials"]["client_id"],
            client_secret=self.config["gcn"]["credentials"]["client_secret"],
            domain=self.config["gcn"]["domain"],
        )
        # available_subscriptions = self.consumer.list_topics().topics
        self.consumer.subscribe(self.config["gcn"].subscriptions)

    def listen(self, timeout=0 * u.s):
        """
        Listen for GCN notices until a given time has passed (default: forever)
        """
        if not isinstance(timeout, u.Quantity):
            # assume seconds if not explicitly given
            timeout = timeout * u.s
        if timeout <= 0 * u.s:
            self.logger.info("Listening indefinitely")
        else:
            self.logger.info("Timeout set to %s", timeout)
        time_start = time.time() * u.s
        while (time.time() * u.s < time_start + timeout) or timeout <= 0 * u.s:
            for message in self.consumer.consume(timeout=1):
                if message.error():
                    self.logger.error(message.error())
                    continue
                self.process_message(message)

    def process_message(self, message):
        """
        Process a message
        """
        message_topic = message.topic()
        self.logger.info("Received message of type %s", message_topic)

        notice_time = datetime.datetime.now()
        self.logger.info(
            "topic=%s, offset=%s\nReceived notice at %s of type %s",
            message.topic(),
            message.offset(),
            notice_time,
            message.topic(),
        )

        try:
            processed_notice = process_gcn_notice(message)
            self.db.add_event(processed_notice)
        except ValueError as e:
            self.logger.error(
                "Failed to process message (type: %s)", message.topic()
            )
            self.logger.error(e)


def receiver(configfile="config.toml", test_message=None):
    """
    Open connection to GCN-Kafka and receive/process messages
    """
    logger = logging.getLogger(__name__)
    if test_message:
        notices = GcnNotices(configfile)
        notices.process_message(test_message)
        return
    # Subscribe to topics and receive alerts
    notices = GcnNotices(configfile)
    logger.info("Connecting...")
    notices.connect()
    logger.info("Listening...")
    notices.listen(timeout=-1 * u.s)


def main():
    """
    Main function
    """
    args = receiver_argument_parser().parse_args()
    logging.basicConfig(
        filename="lo2t.log", encoding="utf-8", level=logging.DEBUG
    )
    logger = logging.getLogger(__name__)
    logger.info("Config file: %s", args.configfile)
    logger.info("Starting receiver")
    receiver(**vars(args))


if __name__ == "__main__":
    main()
