import logging
from urllib.request import urlopen, Request
import lzma

from .table import Table

__all__ = ['HTTPCache']

logger = logging.getLogger(__name__)

class HTTPCache(Table):
    def __init__(self, con, table_name='http_cache', **kwargs):
        super().__init__(con, table_name, [
            'url TEXT PRIMARY KEY',
            'data BLOB NOT NULL',
            'fetch_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL' ], **kwargs)

    def get(self, url, invalidate_days=30, **kwargs):
        c = self.cursor()
        r = self.selectone(cursor=c, fields=('data',), url=url, where="fetch_time > datetime('now', '-%d day')" % invalidate_days)
        if r is not None:
            logger.debug('HTTP result from url %r retrieved from cache.', url)
            return lzma.decompress(r[0])

        logger.info('HTTP query for %r.', url)
        r = urlopen(Request(url, **kwargs)).read()
        self.insert(cursor=c, url=url, data=lzma.compress(r))
        return r
