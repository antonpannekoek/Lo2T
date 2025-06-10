"""
Test heartbeat kafka messages by plotting a dot for each heartbeat received
"""

import json
from gcn_kafka import Consumer
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.animation import FuncAnimation

import dateutil.parser as dateparser
import numpy as np


# Connect as a consumer
# Warning: don't share the client secret with others.
from .credentials import client_id, client_secret

consumer = Consumer(
    client_id=client_id,
    client_secret=client_secret,
)


class Heartbeats:
    """
    Class for keeping track of heartbeats
    """
    def __init__(self):
        self.number_of_heartbeats = 0
        self.heartbeats = []
        self.scat = None
        self.fig, self.ax = plt.subplots()
        self.x = []
        self.y = []

    def process_heartbeat(self, message):
        """
        Parse a heartbeat message: extract the time
        """
        value = message.value()
        data = json.loads(value)
        time = dateparser.parse(data["alert_datetime"])
        self.add_heartbeat(time)

    def add_heartbeat(self, datetime):
        """
        Add a heartbeat datapoint.
        datetime looks like this: 2025-06-10 09:06:19.208966+00:00
        """
        self.number_of_heartbeats += 1
        self.heartbeats.append(datetime)

    def plot_heartbeats(self, x, y):
        """
        Create a new figure and plot the heartbeats
        x axis has the time, y axis the number of heartbeats
        """
        self.scat = self.ax.scatter(x, y)

    def update_figure(self):
        """
        Update figure with new data
        """
        print("Updating figure")
        x = [mdates.date2num(datetime) for datetime in self.heartbeats]
        y = np.arange(self.number_of_heartbeats)
        if self.scat is None:
            self.plot_heartbeats(x, y)
        else:
            self.scat.set_offsets(np.c_[x, y])

        self.ax.set_xlim((x[0], x[-1]))
        self.ax.set_ylim((0, self.number_of_heartbeats + 1))


# Subscribe to topics and receive alerts
consumer.subscribe(["gcn.heartbeat"])
beats = Heartbeats()


def update(frame):
    """
    Update the figure with any new data received
    """
    print(f"Updating - frame {frame}")
    for message in consumer.consume(timeout=1):
        if message.error():
            print(message.error())
            continue
        # Print the topic and message ID
        print(f"topic={message.topic()}, offset={message.offset()}")
        if message.topic() == "gcn.heartbeat":
            beats.process_heartbeat(message)

        beats.update_figure()
        # for key in data:
        #     print(key, data[key])


update(1)
anim = FuncAnimation(beats.fig, update, frames=None)
plt.show()
