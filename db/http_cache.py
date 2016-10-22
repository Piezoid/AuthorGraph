import logging
from urllib.request import urlopen, Request
from urllib.error import URLError
import socket
import gzip

from .table import Table

__all__ = ['HTTPCache']

logger = logging.getLogger(__name__)



class HTTPCache(Table):
    headers = { 'Accept-Encoding': 'gzip'}

    def __init__(self, con, table_name='http_cache', headers=None, timeout=2, retries=5, **kwargs):
        super().__init__(con, table_name, [
            'url TEXT PRIMARY KEY',
            'data BLOB NOT NULL',
            'fetch_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL' ], **kwargs)
        if headers is not None:
            self.headers = self.headers.copy() # Shadow the class attribute with an instance copy
            self.headers.update(headers)
        self.timeout = timeout
        self.retries = retries

    def get(self, url, key=None, cached=True, invalidate_days=30, **kwargs):
        c = self.cursor()
        if key is None:
            key = url
        if cached:
            r = self.selectone(cursor=c, fields=('data',), url=key, where="fetch_time > datetime('now', '-%d day')" % invalidate_days)
            if r is not None:
                logger.debug('HTTP result from url %r retrieved from cache.', url)
                return gzip.decompress(r[0])

        data, compressed = self._urlopen(url, **kwargs)
        self.insert(cursor=c, url=key, data=compressed, replace=True)
        return data

    def _urlopen(self, url, headers=None, **kwargs):
        if headers is None:
            headers = self.headers
        else:
            tmp = self.headers.copy()
            tmp.update(headers)
            headers = tmp

        logger.info('HTTP query for %r.', url)
        for i in range(self.retries):
            try:
                r = urlopen(Request(url, headers=headers, **kwargs), timeout=self.timeout)
                break
            except URLError as e:
                if isinstance(e.reason, socket.timeout) and i < self.retries - 1:
                    logger.warning('Timeout for %r. Retrying...', url)
                    continue
                else:
                    raise e

        data = r.read()
        if r.headers.get('Content-Encoding') == 'gzip':
            return (gzip.decompress(data), data)
        else:
            return (data, gzip.compress(data))
