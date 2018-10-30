import mimetypes
import io
from wsgiref.handlers import format_date_time
from datetime import datetime, timedelta
from time import mktime

from six.moves import urllib

import gevent.monkey
from gevent.pywsgi import WSGIServer

import pymongo.uri_parser
import gridfs
from appsettings import SettingsParser

from khartoum import gzip_util


def get_settings():
    """
    Set up and return the SettingsParser.
    """
    parser = SettingsParser()
    parser.add_argument('--host', default='::0', env_var='HOST')
    parser.add_argument('--port', default=8000, type=int, env_var='PORT')
    parser.add_argument('--mongo_url',
                        default='mongodb://localhost/khartoum.fs',
                        env_var='MONGODB_URL')
    parser.add_argument('--compression_level', default=6, type=int,
                        env_var='COMPRESSION_LEVEL')

    parser.add_argument('--cache_days', default=365, type=int,
                        env_var='CACHE_DAYS')

    settings = parser.parse_args()

    # The set of compressable mimetypes might be configured from a yaml file,
    # but can't be set on the command line or in an env var, so no argument is
    # defined. Instead, just set the default here.
    defaults = [
        'text/plain',
        'text/html',
        'application/javascript',
        'text/css',
    ]
    vars(settings).setdefault('compressable_mimetypes', defaults)

    return settings


class Khartoum(object):
    def __init__(self, db, settings):
        self.db = db
        self.settings = settings
        self.fs = gridfs.GridFS(db, settings.mongo_collection)

    @staticmethod
    def _strip_url(info):
        """
        PATH_INFO may actually be a full URL if the
        request was forwarded from a proxy. Return only
        the path portion.
        """
        return urllib.parse.urlparse(info).path

    def _parse_path(self, info):
        path = self._strip_url(info)
        return path[1:] if path.startswith('/') else path

    def __call__(self, environ, start_response):
        path = self._parse_path(environ['PATH_INFO'])

        qparams = urllib.parse.parse_qs(environ['QUERY_STRING'])
        # The 'v' parameter in the query string may specify
        # a file version, defaulting to -1 (most recent).
        qparams.setdefault('v', [-1])

        version_str, = qparams['v']
        version = int(version_str)
        try:
            f = self.fs.get_version(path, version)
        except gridfs.errors.NoFile:
            start_response("404 NOT FOUND", [('Content-Type', 'text/plain')])
            return io.BytesIO(b"File not found\n")

        headers = [("Vary", "Accept-Encoding")]

        mimetype, encoding = mimetypes.guess_type(f.name)
        if mimetype:
            headers.append(('Content-Type', mimetype))

        if self._use_gzip(mimetype, environ):
            f = gzip_util.compress(f, self.settings.compression_level)
            headers.append(("Content-Encoding", "gzip"))
        else:
            headers.append(('Content-Length', str(f.length)))
            headers.append(('ETag', str(f.md5)))

        if self.settings.cache_days is not None:
            expiration = (datetime.now() +
                          timedelta(days=self.settings.cache_days))
            stamp = mktime(expiration.timetuple())
            headers.append(('Expires', format_date_time(stamp)))

        extra_headers = getattr(self.settings, 'extra_headers', None)
        if extra_headers:
            headers.extend(extra_headers.items())

        start_response("200 OK", headers)
        if environ['REQUEST_METHOD'] == 'GET':
            return f
        else:
            f.close()
            return io.BytesIO(b'')

    def _use_gzip(self, mimetype, environ):
        if mimetype not in self.settings.compressable_mimetypes:
            return False

        encode_header = environ.get('HTTP_ACCEPT_ENCODING', '')
        return gzip_util.gzip_requested(encode_header)


def main():

    gevent.monkey.patch_all()

    settings = get_settings()

    print("Connecting to Mongo at %s." % settings.mongo_url)
    mongo_parsed = pymongo.uri_parser.parse_uri(settings.mongo_url)
    settings.mongo_collection = mongo_parsed['collection']
    c = pymongo.MongoClient(host=settings.mongo_url)
    db = c[mongo_parsed['database']]

    address = settings.host, settings.port
    server = WSGIServer(address, Khartoum(db, settings))
    try:
        print("Khartoum server running on %s:%d. Ctrl+C to quit." % address)
        server.serve_forever()
    except KeyboardInterrupt:
        server.stop()
        print("Khartoum server stopped.")


if __name__ == '__main__':
    main()
