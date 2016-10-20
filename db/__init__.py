import logging
import sqlite3
logger = logging.getLogger(__name__)

from .bibdb import BibDB
from .http_cache import HTTPCache

class DB:
    def __init__(self, dbfile='database.sqlite', drop_cache=False, **kwargs):
        self.con = sqlite3.connect(dbfile, detect_types=sqlite3.PARSE_DECLTYPES)

        self.http_cache = HTTPCache(self.con, recreate=drop_cache)
        self.bibdb = BibDB(self.con, **kwargs)
