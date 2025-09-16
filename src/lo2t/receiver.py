"""
Receive Kafka GCN messages
"""

import os
import logging
import time
import datetime
import argparse
import json
import tomllib
from functools import reduce
from gcn_kafka import Consumer

import dateutil.parser as dateparser
import numpy as np
import astropy.units as u

from .db import Lo2tDb
from .decode import process_gcn_notice


def get_nested_value(nested_dict, keys):
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

    def __init__(self, configfile="config.toml", verbose=0):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(10 - verbose * 10)
        self.consumer = None
        self.notice_counter = {}
        self.notice_limit = {}
        self.notice_type = {}
        self.messages = []
        self.config = self.load_config(configfile)
        self.db = Lo2tDb(self.config)

    def load_config(self, configfile):
        """
        Load config file
        """
        with open(configfile, "rb") as f:
            config = tomllib.load(f)
        self.domain = config["gcn"]["domain"]
        self.subscriptions = config["gcn"]["subscriptions"]
        credentials = config["gcn"]["credentials"]
        self.__client_id = credentials["client_id"]
        self.__client_secret = credentials["client_secret"]
        for subscription in self.subscriptions:
            self.notice_counter[subscription] = 0
            try:
                subscription_config = get_nested_value(
                    config, subscription.split(".")
                )
            except KeyError:  # in case of nested config
                subscription_config = get_nested_value(
                    config, subscription.split(".")[:-1]
                )
            self.notice_limit[subscription] = subscription_config["limit"]
            self.notice_type[subscription] = subscription_config["message_type"]

            self.logger.info(f"Registered for {subscription} notices")
        return config

    def connect(self):
        """
        Connect as a consumer
        Warning: don't share the client secret with others.
        """
        self.consumer = Consumer(
            client_id=self.__client_id,
            client_secret=self.__client_secret,
            domain=self.domain,
        )
        # available_subscriptions = self.consumer.list_topics().topics
        self.consumer.subscribe(self.subscriptions)

    def extract_time(self, message):
        """
        Extract the time from a notice
        """
        value = message.value()
        data = json.loads(value)
        notice_time = dateparser.parse(data["alert_datetime"])
        return notice_time

    def save_message(self, message, notice_time, outdir="notices"):
        "Save the message to a file"
        # make sure the output dir exists
        if not os.path.exists(outdir):
            os.makedirs(outdir)

        # message.topic()
        filename = f"{outdir}/{message.topic()}_notice_{notice_time}"
        filetype = self.notice_type[message.topic()]
        if filetype == "json":
            filename += ".json"
        elif filetype == "voevent":
            filename += ".voevent"

        if filetype == "json":
            with open(
                filename,
                "w",
            ) as f:
                json.dump(json.loads(message.value()), f, indent=4)
        elif filetype == "voevent":
            with open(
                filename,
                "wb",
            ) as f:
                f.write(message.value())

        self.logger.info(
            "Saved message to file %s", filename
        )

    def listen(self, timeout=100 * u.s):
        """
        Listen for GCN notices until a given time has passed
        """
        if not isinstance(timeout, u.Quantity):
            # assume seconds if not explicitly given
            timeout = timeout * u.s
            self.logger.info("Timeout set to %s", timeout)
        time_start = time.time() * u.s
        while (
            (time.time() * u.s < time_start + timeout)
            or timeout < 0
        ):
            for message in self.consumer.consume(timeout=1):
                if message.error():
                    self.logger.error(message.error())
                    continue
                self.parse_message(message)

    def parse_message(self, message):
        """
        Parse a message
        """
        self.notice_counter[message.topic()] += 1
        # optional limiter on how many messages of each type to process
        if (
            self.notice_limit[message.topic()]
            > self.notice_counter[message.topic()]
            or self.notice_limit[message.topic()] < 0
        ):
            message_topic = message.topic()
            self.logger.info("Received message of type %s", message_topic)
            # Based on the message topic, choose the right decoder

            # Print the topic and message ID
            try:
                if self.notice_type[message.topic()] == "json":
                    notice_time = self.extract_time(message)
                elif self.notice_type[message.topic()] == "voevent":
                    self.logger.info(
                        "not a json message, setting notice_time to current time"
                    )
                    notice_time = datetime.datetime.now()
            except KeyError:
                self.logger.error(
                    "No alert_datetime key in message of type %s "
                    + "Setting notice_time to current time",
                    message.topic(),
                )
                notice_time = datetime.datetime.now()

            self.logger.info(
                "topic=%s, offset=%s\n"
                "Received notice at %s of type %s\n"
                "(number %d out of %d)",
                message.topic(), message.offset(), notice_time, message.topic(),
                self.notice_counter[message.topic()],
                self.notice_limit[message.topic()],
            )

            self.save_message(message, notice_time)

        if (
            self.notice_counter[message.topic()]
            == self.notice_limit[message.topic()]
        ):
            self.logger.info(
                "Received %s notices of type %s"
                " - stopping listening to these notices",
                self.notice_limit[message.topic()], message.topic()
            )


def receiver(configfile="config.toml", test_message=None, **kwargs):
    logger = logging.getLogger(__name__)
    if test_message:
        notices = GcnNotices(configfile)
        notices.parse_message(test_message)
        return
    # Subscribe to topics and receive alerts
    notices = GcnNotices(configfile)
    logger.info("Connecting...")
    notices.connect()
    logger.info("Listening...")
    notices.listen(timeout=-1 * u.s)


def main():
    args = receiver_argument_parser().parse_args()
    logging.basicConfig(filename="lo2t.log", encoding="utf-8", level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    logger.info("Config file: %s", args.configfile)
    logger.info("Starting receiver")
    receiver(**vars(args))


if __name__ == "__main__":
    main()
