"""
Find a calibrator source
"""
import pandas
from astropy.coordinates import SkyCoord


class Calibrator:
    def add_calibrator(self):
        pass


# Old code with modifications
def find_calibrator(
    time,  # time of observation
    ra,  # ra of observation
    dec,  # dec of observation
    time_dwell_max,
    time_dwell_min,
    time_obs_max,
    time_obs_min,
):
    calibrators = pandas.read_csv("calibrators.csv", sep=",", header=0)
    separation = 648000.0
    optcalFound = False
    for index2, cal in calibrators.iterrows():
        c1 = SkyCoord(ra, dec, unit="deg")
        c2 = SkyCoord(float(cal.ra), float(cal.dec), unit="deg")
        septmp = c1.separation(c2)
        septmp = septmp.arcsecond
        startT = time + timedelta(minutes=time_dwell_min)
        time_start = startT + timedelta(minutes=time_obs_max + time_dwell_max + 2.0)
        time_end = time_start + timedelta(minutes=CalObsT)

        altitude_at_start = calc_alt_az(
            time_start, ra, dec, LOFARlocation
        )  # check altitude of calibrator at start of observation
        altitude_at_end = calc_alt_az(
            time_end, ra, dec, LOFARlocation
        )  # check altitude of calibrator at end of observation
        if (
            septmp < separation
            and altitude_at_start > AltCut
            and altitude_at_end > AltCut
        ):
            # if calibrator is above min elevation for duration and is closer
            # than previous calibrator, it becomes the optimum calibrator
            separation = septmp
            optcalFound = True
            optcal = cal.src
            optra = cal.ra
            optdec = cal.dec
    if optcalFound:
        return {
            "Calibrators": optcal,
            "CalSep": (separation / (60.0 * 60.0)),
            "CalRA": optra,
            "CalDec": optdec,
        }
    else:
        return {"Calibrators": "None", "CalSep": 0, "CalRA": 0, "CalDec": 0}


