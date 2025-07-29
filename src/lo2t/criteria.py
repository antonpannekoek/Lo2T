import astropy.units as u
from astropy.coordinates import EarthLocation


class TriggerCriteria:
    def __init__(self):
        pass


class GWTriggerCriteria(TriggerCriteria):
    def __init__(self):
        super().__init__()
        self.gw_has_neutron_star = 0.8
        self.gw_has_remnant = 0.5
        self.gw_terrestrial_possibility_max = 0.01
        self.gw_number_of_detectors = 3
        

class GRBTriggerCriteria(TriggerCriteria):
    def __init__(self):
        super().__init__()
        self.grb_trigger_duration = 2.0 * u.s
        self.grb_rate_significance = 10.0


class LofarTriggerCriteria(TriggerCriteria):
    def __init__(self):
        super().__init__()
        self.lofar_observation_max_time = 120.0 * u.minute
        self.lofar_altitute_minimum = 20 * u.deg
        self.lofar_dwell_time_maximum = 8.0 * u.minute
        self.lofar_dwell_time_minimum = 4.0 * u.minute
        self.lofar_location = EarthLocation.of_site("LOFAR")
