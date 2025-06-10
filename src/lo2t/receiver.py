"""
Receive Kafka GCN messages
"""

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
        "--config",
        default="config.toml",
        help="Path to configuration file",
    )
    return parser


class GcnNotices:
    """
    Class for receiving and keeping track of GCN notices
    """

    def __init__(self, configfile):
        self.consumer = None
        self.notice_counter = {}
        self.notice_limit = {}
        self.messages = []
        self.config = self.load_config(configfile)

    def load_config(self, configfile):
        """
        Load config file
        """
        with open(configfile, "rb") as f:
            config = tomllib.load(f)
        self.subscriptions = config["gcn"]["subscriptions"]
        credentials = config["gcn"]["credentials"]
        self.__client_id = credentials["client_id"]
        self.__client_secret = credentials["client_secret"]
        for subscription in self.subscriptions:
            self.notice_counter[subscription] = 0
            self.notice_limit[subscription] = get_nested_value(
                config, subscription.split(".")
            )["limit"]
            print(f"Listening for {subscription} notices")
        return config

    def connect(self):
        """
        Connect as a consumer
        Warning: don't share the client secret with others.
        """
        self.consumer = Consumer(
            client_id=self.__client_id,
            client_secret=self.__client_secret,
        )
        self.consumer.subscribe(self.subscriptions)

    def extract_time(self, message):
        """
        Extract the time from a notice
        """
        value = message.value()
        data = json.loads(value)
        notice_time = dateparser.parse(data["alert_datetime"])
        return notice_time

    def listen(self, timeout=100 * u.s):
        """
        Listen for GCN notices until a given time has passed
        """
        if not isinstance(timeout, u.Quantity):
            # assume seconds if not explicitly given
            timeout = timeout * u.s
            print(f"Timeout set to {timeout}")
        time_start = time.time() * u.s
        while (
            (time.time() * u.s < time_start + timeout)
            or timeout < 0
        ):
            for message in self.consumer.consume(timeout=1):
                if message.error():
                    print(message.error())
                    continue
                self.notice_counter[message.topic()] += 1
                if (
                    self.notice_limit[message.topic()]
                    > self.notice_counter[message.topic()]
                    or self.notice_limit[message.topic()] < 0
                ):
                    # Print the topic and message ID
                    try:
                        notice_time = self.extract_time(message)
                    except KeyError:
                        print(f"No alert_datetime key in message of type {message.topic()}")
                        print("Setting notice_time to current time")
                        notice_time = datetime.datetime.now()
                    print(
                        f"topic={message.topic()}, offset={message.offset()}\n"
                        f"Received notice at {notice_time} of type {message.topic()}\n"
                        f"(number {self.notice_counter[message.topic()]}"
                        f" out of {self.notice_limit[message.topic()]})"
                    )
                    # Save the message to a file
                    filename = f"{message.topic()}_notice_{notice_time}.json"
                    with open(
                        filename,
                        "w",
                    ) as f:
                        json.dump(json.loads(message.value()), f, indent=4)
                    print(
                        f"Saved message to {filename}"
                    )

                if (
                    self.notice_counter[message.topic()]
                    == self.notice_limit[message.topic()]
                ):
                    print(
                        f"Received {self.notice_limit[message.topic()]} "
                        f"notices of type {message.topic()}"
                        f" - stopping listening to these notices"
                    )


def receiver(configfile):
    # Subscribe to topics and receive alerts
    notices = GcnNotices(configfile)
    notices.connect()
    notices.listen(timeout=-1 * u.s)


def main():
    parser = receiver_argument_parser()
    args = parser.parse_args()
    receiver(args.config)


if __name__ == "__main__":
    main()
