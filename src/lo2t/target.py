"""
Observation target
"""
import pandas as pd

class ObservationTarget:
    """
    Class that contains all relevant information for an observation target.
    To be used as a superclass.
    """
    def __init__(self):
        self.ra = None
        self.dec = None
        self.band = None
        self.name = None
        self.calibrator = None

    def set_ra_dec(self, ra, dec):
        """
        Sets the right ascension and declination of the target
        """
        self.ra = ra
        self.dec = dec

    def find_calibrator(self, filename="calibrators.csv"):
        """
        Reads the calibrator information from a csv file, and finds an
        appropriate calibrator.
        """
        self.calibrators = pd.read_csv(filename, sep=",", header=0)
