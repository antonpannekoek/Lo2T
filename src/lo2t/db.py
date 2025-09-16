"""
Store events in database and check if two events match id/time/location.
"""
import time
import datetime
import sqlite3
import tempfile
import astropy.units as u
import astropy_healpix

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
    def __init__(self, db_path):
        self.table = "events"
        self.healpix_nside = 128  # healpix resolution, about half a degree
        if db_path is None:
            db_path = tempfile.NamedTemporaryFile().name
        self.db = sqlite3.connect(db_path)
        self.cur = self.db.cursor()
        self.cur.execute(
            f"CREATE TABLE IF NOT EXISTS "
            f"{self.table} ("
            f"id TEXT PRIMARY KEY, "
            f"time TIMESTAMP, "
            f"ra REAL, "
            f"ra_err REAL, "
            f"ra_unit TEXT, "
            f"dec REAL, "
            f"dec_err REAL, "
            f"dec_unit TEXT, "
            f"healpix_index_128 INTEGER, "
            f"data BLOB)"
        )

    def commit(self):
        self.db.commit()

    def close(self):
        self.commit()
        self.db.close()

    def add_event(self, event):
        self.cur.execute(
            f"INSERT INTO {self.table} ("
            f"id, "
            f"time, "
            f"ra, "
            f"ra_err, "
            f"ra_unit, "
            f"dec, "
            f"dec_err, "
            f"dec_unit, "
            f"healpix_index_128, "
            f"data"
            f") VALUES ("
            f"?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                event.id,
                event.time,
                event.ra.value,
                event.ra_err.value,
                event.ra.unit,
                event.dec.value,
                event.dec_err.value,
                event.dec.unit,
                astropy_healpix.lonlat_to_healpix(
                    event.ra,
                    event.dec,
                    nside=self.healpix_nside,
                ),
                event.data,
            ),
        )
        self.commit()

    def get_event(self, event_id):
        self.cur.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        return self.cur.fetchone()

    def is_duplicate(self, event):
        self.cur.execute("SELECT * FROM events WHERE id = ?", (event.id,))
        return self.cur.fetchone()

    def is_near_in_position(self, event):
        # Use HEALPix to find all events within tolerance_position.
        # We assume that is the same HEALPix index or one of its neighbors.
        # So select all events with the same index or a neighbor index.

        neighbor_indices = astropy_healpix.get_neighbors(
            event.healpix_index_128, nside=self.healpix_nside
        )
        neighbor_indices.append(event.healpix_index_128)

        self.cur.execute(
            f"SELECT * FROM {self.table} WHERE "
            f"healpix_index_128 IN ({','.join(['?'] * len(neighbor_indices))})",
            neighbor_indices,
        )
        return self.cur.fetchall()

    def is_near_in_time(self, event, tolerance_time=10 * u.minute):
        self.cur.execute(
            f"SELECT * FROM {self.table} WHERE "
            f"time BETWEEN ? AND ?",
            (event.time - tolerance_time, event.time + tolerance_time),
        )
        return self.cur.fetchall()

    def cleanup_old_events(self, tolerance_time=60 * u.minute):
        self.cur.execute(
            f"DELETE FROM {self.table} WHERE "
            f"time < ?",
            (datetime.datetime.now() - tolerance_time,),
        )
        self.commit()

    def update_event(self, event):
        self.cur.execute(
            f"UPDATE {self.table} SET "
            f"time = ?, "
            f"ra = ?, "
            f"ra_err = ?, "
            f"ra_unit = ?, "
            f"dec = ?, "
            f"dec_err = ?, "
            f"dec_unit = ?, "
            f"healpix_index_128 = ?, "
            f"data = ? "
            f"WHERE id = ?",
            (
                event.time,
                event.ra.value,
                event.ra_err.value,
                event.ra.unit,
                event.dec.value,
                event.dec_err.value,
                event.dec.unit,
                astropy_healpix.lonlat_to_healpix(
                    event.ra,
                    event.dec,
                    nside=self.healpix_nside,
                ),
                event.data,
                event.id,
            )
        )
        self.commit()
