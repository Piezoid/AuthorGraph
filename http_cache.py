import logging
#from urllib.request import urlopen, Request
#from urllib.error import URLError
#import socket
import requests
import gzip
import pickle
import datetime

__all__ = ['HTTPCache']

logger = logging.getLogger(__name__)



class HTTPCache:
    def __init__(self, file_name='http_cache.pk', timeout=5, retries=5):
        self.file_name = file_name
        try:
            self.cache = pickle.load(open(file_name, 'rb'))
            logger.info('Loaded HTTP cache from %r', self.file_name)
        except FileNotFoundError:
            self.cache = {}
        self.timeout = timeout
        self.retries = retries
        self.used = set()
        self.session = requests.Session()

    def close(self):
        self.session.close()

    def save(self, only_used=False):
        if only_used:
            used = self.used
            cache = {k:v for k,v in self.cache.items() if k in used}
        else:
            cache = self.cache
        pickle.dump(cache, open(self.file_name, 'wb'))
        logger.info('HTTP cache saved to %r', self.file_name)

    def __del__(self):
        self.close()
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

    def _urlopen(self, url, **kwargs):
        logger.info('HTTP query for %r.', url)
        for i in range(self.retries):
            try:
                r = self.session.get(url, stream=True,
                                     timeout=self.timeout, **kwargs)
                data = r.raw.read()
            except requests.RequestException as e:
                if i+1 >= self.retries:
                    raise e
                else:
                    logger.warning('%r for %r. Retrying...', e, url)
                    continue
            finally:
                r.close()
        if r.headers.get('Content-Encoding') == 'gzip':
            return (gzip.decompress(data), data)
        else:
            return (data, gzip.compress(data))


