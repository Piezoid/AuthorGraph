import logging
from urllib.request import urlopen, Request
from urllib.error import URLError
import socket
import gzip
import pickle
import datetime

__all__ = ['HTTPCache']

logger = logging.getLogger(__name__)



class HTTPCache:
    headers = { 'Accept-Encoding': 'gzip'}

    def __init__(self, file_name='http_cache.pk', headers=None, timeout=5, retries=5):
        self.file_name = file_name
        try:
            self.cache = pickle.load(open(file_name, 'rb'))
            logger.info('Loaded HTTP cache from %r', self.file_name)
        except FileNotFoundError:
            self.cache = {}
        if headers is not None:
            self.headers = self.headers.copy() # Shadow the class attribute with an instance copy
            self.headers.update(headers)
        self.timeout = timeout
        self.retries = retries
        self.used = set()

    def save(self, only_used=False):
        if only_used:
            used = self.used
            cache = {k:v for k,v in self.cache.items() if k in used}
        else:
            cache = self.cache
        pickle.dump(cache, open(self.file_name, 'wb'))
        logger.info('HTTP cache saved to %r', self.file_name)

    def __del__(self):
        self.save()

    def get(self, url, key=None, cached=True, invalidate_days=30, **kwargs):
        if key is None:
            key = url
        self.used.add(key)
        if cached:
            data = self.cache.get(key)
            if data is not None:
                data, date = data
                if date > datetime.datetime.now() - datetime.timedelta(days=invalidate_days):
                    return gzip.decompress(data)

        data, compressed = self._urlopen(url, **kwargs)
        self.cache[key] = (compressed, datetime.datetime.now())
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
                data = r.read()
                if r.headers.get('Content-Encoding') == 'gzip':
                    return (gzip.decompress(data), data)
                else:
                    return (data, gzip.compress(data))

            except URLError as e:
                logger.warning('%r for %r. Retrying...', e, url)
                continue
            except socket.timeout:
                logger.warning('timeout for %r. Retrying...', url)
                continue



