"""
Store events in database and check if two events match id/time/location.
"""
import time
import datetime
import sqlite3
import tempfile
import astropy.units as u
import astropy_healpix as ah

import numpy as np


def adapt_datetime_iso(val):
    """Adapt datetime.datetime to timezone-naive ISO 8601 date."""
    return val.replace(tzinfo=datetime.timezone.utc).isoformat()


def convert_datetime(val):
    """Convert ISO 8601 datetime to datetime.datetime object."""
    return datetime.datetime.fromisoformat(val.decode())


sqlite3.register_adapter(datetime.datetime, adapt_datetime_iso)
sqlite3.register_converter("datetime", convert_datetime)


class Lo2tDb:
    """
    Store (and retrieve) events in database.
    """

    def __init__(self, config):
        db_path = config["lo2t"]["db_path"]
        self.event_table = config["lo2t"]["db_table"]
        self.trigger_table = config["lo2t"]["db_table"]
        self.healpix_nside = config["lo2t"]["healpix_nside"]
        self.timezone_utc_offset = config["lo2t"]["timezone_utc_offset"]
        self.hp = ah.HEALPix(nside=self.healpix_nside, order='nested')

        if db_path is None:
            db_path = tempfile.NamedTemporaryFile().name
        self.db = sqlite3.connect(db_path)
        self.cur = self.db.cursor()

        # Create a table storing settings
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS "
            "settings ("
            "name TEXT PRIMARY KEY, "
            "value TEXT)"
        )
        # store settings
        self.store_setting("healpix_nside", self.healpix_nside)
        self.store_setting("timezone_utc_offset", self.timezone_utc_offset)

        # Check if a start time is stored
        try:
            self.cur.execute("SELECT value FROM settings WHERE name = 'start_time'")
            self.start_time = float(self.cur.fetchone()[0]) * u.s
        except TypeError:
            self.start_time = None
        if self.start_time is None:
            self.start_time = time.time() * u.s
            self.store_setting("start_time", self.start_time.to_value(u.s))
        print(f"Start time: {self.start_time}")

        # Create a table storing events
        self.cur.execute(
            f"CREATE TABLE IF NOT EXISTS "
            f"{self.event_table} ("
            f"id TEXT PRIMARY KEY, "  # event id from GCN
            f"topic TEXT, "  # topic from GCN
            f"alert_type TEXT, "  # event type from GCN
            f"time_utc TIMESTAMP, "  # time from GCN
            f"time_created TIMESTAMP, "  # time when event was created in database
            f"time_modified TIMESTAMP, "  # time when event was last modified
            f"ra REAL, "  # right ascension, units depend on ra_unit
            f"ra_err REAL, "  # error in ra
            f"ra_unit TEXT, "  # rad or deg
            f"dec REAL, "  # declination, units depend on dec_unit
            f"dec_err REAL, "  # error in dec
            f"dec_unit TEXT, "  # rad or deg
            f"healpix_index INTEGER, "  # HEALPix index, composed from ra,dec
            f"terrestrial_chance REAL, "  # chance of event being terrestrial
            f"false_alarm_rate REAL, "  # chance of event being false alarm
            f"has_neutron_star INTEGER, "  # 1 if event has a neutron star, 0 otherwise
            f"has_remnant INTEGER, "  # 1 if event has a remnant, 0 otherwise
            f"data BLOB)"  # store any additional data
        )
        # Create a table storing triggers sent
        self.cur.execute(
            f"CREATE TABLE IF NOT EXISTS "
            f"{self.trigger_table} ("
            f"id TEXT PRIMARY KEY, "  # think of something for this
            f"event_id TEXT, "  # event id from GCN used to trigger
            f"ra REAL, "  # right ascension, units depend on ra_unit
            f"ra_unit TEXT, "  # rad or deg
            f"dec REAL, "  # declination, units depend on dec_unit
            f"dec_unit TEXT, "  # rad or deg
            f"exposure_time INTEGER, "  # exposure time in seconds
            f"calibrator_id TEXT, "  # id of calibrator
            f"calibrator_ra REAL, "  # ra of calibrator
            f"calibrator_ra_unit TEXT, "  # rad or deg
            f"calibrator_dec REAL, "  # dec of calibrator
            f"calibrator_dec_unit TEXT, "  # rad or deg
            f"calibrator_exposure_time INTEGER )"  # calibrator exposure time in seconds
        )


    def store_setting(self, name, value, overwrite=False):
        # Store settings. If the setting already exists, issue a warning or
        # ignore, depending on overwrite keyword.
        self.cur.execute(
            f"INSERT OR {'IGNORE' if overwrite else 'REPLACE'} INTO settings "
            f"(name, value) VALUES (?, ?)",
            (name, value),
        )
        self.commit()

    def store_data(self, data, index, column, table, commit=True):
        """Stores data in the database.
        If data and column are lists, store multiple values.
        """

        self.cur.execute(
            f"UPDATE {table} SET {column} = ? WHERE id = ?",
            (data, index),
        )
        if commit:
            self.commit(index)

    def commit(self, index=None):
        """Set modified time and commit changes to database."""
        if index is None:
            self.db.commit()
            return
        self.db.commit()
        # modified_time = (time.time() * u.s) - self.start_time
        modified_time = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        self.cur.execute(
            f"UPDATE {self.event_table} SET time_modified = ? WHERE id = ?",
            (modified_time, index),
        )
        self.db.commit()

    def close(self):
        self.db.close()

    # Getters
    def get_event(self, event_id):
        """Get event from database by id, and retrieve all attributes."""
        self.cur.execute(f"SELECT * FROM {self.event_table} WHERE id = ?", (event_id,))
        return self.cur.fetchone()

    def get_index(self, event):
        return event.index

    # Adder
    def add_event(self, event):
        """Adds a new event to the database."""
        index = self.get_index(event)

        # Check if the event is already in the database
        self.cur.execute(f"SELECT id FROM {self.event_table} WHERE id = ?", (index,))
        if self.cur.fetchone() is not None:
            print(f"Event {index} already in database, updating...")
        else:
            print(f"Adding event {index}")
            self.create_event(event)
        self.set_alert_type(event)
        self.set_time(event)
        self.set_position(event)
        self.set_position_error(event)
        self.set_healpix_index(event)
        self.set_skymap(event)
        self.set_terrestrial_chance(event)
        self.set_false_alarm_rate(event)
        self.set_has_neutron_star(event)
        self.set_has_remnant(event)
        return 0

    # Creator
    def create_event(self, event):
        """Adds a new event to the database. Only stores the index at this time."""
        index = self.get_index(event)
        try:
            index = event.index
        except AttributeError:
            print("No index, cannot add event")
            return -1
        try:
            topic = event.topic
        except AttributeError:
            print("No topic, cannot add event")
            return -1

        self.cur.execute(f"INSERT INTO {self.event_table} (id) VALUES (?)", (index,))

        self.cur.execute(
            f"UPDATE {self.event_table} SET topic = ? WHERE id = ?",
            (topic, index),
        )

        time_created = datetime.datetime.now().strftime(
            "%Y-%m-%dT%H:%M:%S.%fZ",
        )
        self.cur.execute(
            f"UPDATE {self.event_table} SET time_created = ? WHERE id = ?",
            (time_created, index),
        )

        self.commit(index)
        print(f"Added event {index}")
        return 0

    # Setters
    def set_alert_type(self, event):
        """Stores the alert type of the event in the database."""
        index = self.get_index(event)
        try:
            alert_type = event.alert_type
        except AttributeError:
            print("No alert type")
            return -1

        self.cur.execute(
            f"UPDATE {self.event_table} SET alert_type = ? WHERE id = ?",
            (alert_type, index)
        )
        self.commit(index)
        return 0

    def set_time(self, event):
        """Stores the time of the event in the database."""
        index = self.get_index(event)
        try:
            time = event.time
        except AttributeError:
            print("No time")
            return -1

        self.cur.execute(
            f"UPDATE {self.event_table} SET time_utc = ? WHERE id = ?",
            (time, index)
        )
        self.commit(index)
        return 0

    def set_position(self, event):
        """Stores the position of the event in the database."""
        index = self.get_index(event)
        try:
            ra, dec = event.position
        except AttributeError:
            print("No position")
            return -1

        print(f"Position: {ra} {dec}")
        try:
            print(ra.value)
        except AttributeError:
            print("cannot print ra.value")
        try:
            print(ra.unit)
        except AttributeError:
            print("cannot print ra.unit")
        try:
            ra_unit = str(ra.unit)
            dec_unit = str(dec.unit)
            ra = ra.value
            dec = dec.value
        except AttributeError as e:
            print(e)
            print("Position has no unit")
            return -2
        print(f"Storing position: {ra} {dec}")
        print(f"Storing position units: {ra_unit} {dec_unit}")
        self.cur.execute(
            f"UPDATE {self.event_table} SET "
            f"ra = ?, "
            f"ra_unit = ?, "
            f"dec = ?, "
            f"dec_unit = ? "
            f"WHERE id = ?",
            (ra, ra_unit, dec, dec_unit, index),
        )
        print(f"Storing position {ra} {ra_unit} {dec} {dec_unit}")
        self.commit(index)
        return 0

    def set_position_error(self, event):
        """Stores the position error of the event in the database."""
        index = self.get_index(event)
        try:
            ra_err, dec_err = event.position_err
        except AttributeError:
            print("No position error")
            return -1
        try:
            ra_err = ra_err.value
            dec_err = dec_err.value
        except AttributeError:
            pass

        self.cur.execute(
            f"UPDATE {self.event_table} SET "
            f"ra_err = ?, "
            f"dec_err = ? "
            f"WHERE id = ?",
            (ra_err, dec_err, index),
        )
        self.commit(index)
        return 0

    def set_healpix_index(self, event):
        """Stores the HEALPix index of the event in the database."""
        index = self.get_index(event)
        try:
            healpix_index = int(event.healpix_index)
        except (AttributeError, TypeError):
            print("No HEALPix index")
            try:
                ra, dec = event.position
                healpix_index = self.hp.lonlat_to_healpix(ra, dec)
                print(f"Calculated HEALPix index: {healpix_index}")
            except AttributeError:
                print("Could not calculate HEALPix index")
                return -1

        self.cur.execute(
            f"UPDATE {self.event_table} SET healpix_index = ? WHERE id = ?",
            (int(healpix_index), index),
        )
        print(f"Storing HEALPix index {healpix_index}")
        print(f"{healpix_index.dtype}")
        self.commit(index)
        return 0

    def set_exposure_time(self, event):
        """Stores the exposure time of the event in the database."""
        index = self.get_index(event)
        table = self.triggers_table
        column = "exposure_time"
        try:
            exposure_time = event.exposure_time
        except AttributeError:
            print("No exposure time")
            return -1

        self.store_data(exposure_time, index, column, table)
        return 0

    def set_calibrator_name(self, event):
        """Stores the calibrator name of the event in the database."""
        index = self.get_index(event)
        try:
            calibrator_name = event.calibrator_name
        except AttributeError:
            print("No calibrator name")
            return -1

        self.cur.execute(
            f"UPDATE {self.event_table} SET calibrator_name = ? WHERE id = ?",
            (calibrator_name, index),
        )
        self.commit(index)
        return 0

    def set_calibrator_position(self, event):
        """Stores the calibrator position of the event in the database."""
        index = self.get_index(event)
        try:
            calibrator_ra, calibrator_dec = event.calibrator_position
            ra = calibrator_ra.value
            dec = calibrator_dec.value
            ra_unit = calibrator_ra.unit
            dec_unit = calibrator_dec.unit
        except AttributeError:
            print("No calibrator position")
            return -1

        self.cur.execute(
            f"UPDATE {self.event_table} SET "
            f"calibrator_ra = ?, "
            f"calibrator_ra_unit = ?, "
            f"calibrator_dec = ? "
            f"calibrator_dec_unit = ? "
            f"WHERE id = ?",
            (
                ra,
                ra_unit,
                dec,
                dec_unit,
                index,
            ),
        )
        self.commit(index)
        return 0

    def set_calibrator_exposure_time(self, event):
        """Stores the calibrator exposure time of the event in the database."""
        index = self.get_index(event)
        table = self.event_table
        column = "calibrator_exposure_time"
        try:
            value = event.calibrator_exposure_time
        except AttributeError:
            print("No calibrator exposure time")
            return -1

        self.store_data(value, index, column, table)
        return 0

    def set_skymap(self, event):
        """Stores the skymap of the event in the database."""
        index = self.get_index(event)
        table = self.event_table
        column = "data"
        try:
            value = event.skymap
        except AttributeError:
            print("No skymap")
            return -1

        self.store_data(value, index, column, table)
        return 0

    def set_terrestrial_chance(self, event):
        """Stores the terrestrial chance of the event in the database."""
        index = self.get_index(event)
        table = self.event_table
        column = "terrestrial_chance"
        try:
            value = event.terrestrial_chance
        except AttributeError:
            print("No terrestrial chance")
            return -1

        self.store_data(value, index, column, table)
        return 0

    def set_false_alarm_rate(self, event):
        """Stores the false alarm rate of the event in the database."""
        index = self.get_index(event)
        table = self.event_table
        column = "false_alarm_rate"
        try:
            value = event.false_alarm_rate
        except AttributeError:
            print("No false alarm rate")
            return -1

        self.store_data(value, index, column, table)
        return 0

    def set_has_neutron_star(self, event):
        """Stores the has_neutron_star of the event in the database."""
        index = self.get_index(event)
        table = self.event_table
        column = "has_neutron_star"
        try:
            value = event.has_neutron_star
        except AttributeError:
            print("No has_neutron_star")
            return -1

        self.store_data(value, index, column, table)
        return 0

    def set_has_remnant(self, event):
        """Stores the has_remnant of the event in the database."""
        index = self.get_index(event)
        table = self.event_table
        column = "has_remnant"
        try:
            value = event.has_remnant
        except AttributeError:
            print("No has_remnant")
            return -1

        self.store_data(value, index, column, table)
        return 0

    # Checks
    def is_duplicate(self, event):
        """Returns True if the event is already in the database."""
        return bool(self.get_event(event.index))

    def is_near_in_position(self, event):
        # Use HEALPix to find all events within tolerance_position.
        # We assume that is the same HEALPix index or one of its neighbours.
        # So select all events with the same index or a neighbour index.

        neighbour_indices = ah.neighbours(
            event.healpix_index, nside=self.healpix_nside
        )
        neighbour_indices.append(event.healpix_index)

        self.cur.execute(
            f"SELECT * FROM {self.event_table} WHERE "
            f"healpix_index IN ({','.join(['?'] * len(neighbour_indices))})",
            neighbour_indices,
        )
        return self.cur.fetchall()

    def is_near_in_time(self, event, tolerance_time=10 * u.minute):
        self.cur.execute(
            f"SELECT * FROM {self.event_table} WHERE time_utc BETWEEN ? AND ?",
            (event.time - tolerance_time, event.time + tolerance_time),
        )
        return self.cur.fetchall()

    # Cleanup
    def cleanup_old_events(self, tolerance_time=60 * u.minute):
        now = datetime.datetime.now() * u.s
        self.cur.execute(
            f"DELETE FROM {self.event_table} WHERE time_utc < ?",
            (now - tolerance_time).to_value(u.s),
        )
        self.commit()
