"""
Take an event location (ra, dec) and return the alt, az for a given observation
site (by default: LOFAR).
"""

from astropy.coordinates import (
    SkyCoord, EarthLocation, AltAz
)


def radec_to_altaz(ra, dec, time, site="LOFAR"):
    """
    Take an event location (ra, dec) and return the alt, az for a given
    observation site (by default: LOFAR).

    Arguments:
    ra (float): Right Ascension
    dec (float): Declination
    time (datetime): Time of observation
    site (str): Observation site
    """
    location = EarthLocation.of_site(site)
    coord = SkyCoord(ra=ra, dec=dec)

    altaz = coord.transform_to(AltAz(obstime=time, location=location))
    return altaz.alt, altaz.az
