import mimetypes
import urlparse
from wsgiref.handlers import format_date_time
from datetime import datetime, timedelta
from time import mktime

from gevent.pywsgi import WSGIServer
from gevent import monkey

# monkeypatch all socket things before importing pymongo.
monkey.patch_all()

import pymongo
from pymongo.uri_parser import parse_uri as parse_mongo_uri
import gridfs
from appsettings import SettingsParser

from khartoum import gzip_util


def get_settings():
    """
    Set up and return the SettingsParser.
    """
    parser = SettingsParser()
    parser.add_argument('--host', default='0.0.0.0', env_var='HOST')
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
    # but can't be set on the command line or in an env var, so we don't add an
    # argument for that.  Instead, just stick the default on right here if a
    # config file hasn't already set it.
    if not hasattr(settings, 'compressable_mimetypes'):
        settings.compressable_mimetypes = [
            'text/plain',
            'text/html',
            'application/javascript',
            'text/css',
        ]

    return settings


class Khartoum(object):
    def __init__(self, db, settings):
        self.db = db
        self.settings = settings
        self.fs = gridfs.GridFS(db, settings.mongo_collection)

    def __call__(self, environ, start_response):
        # PATH_INFO may actually be a full URL, if the request was forwarded
        # from a proxy.
        path = urlparse.urlparse(environ['PATH_INFO']).path
        if path.startswith('/'):
            path = path[1:]

        qparams = urlparse.parse_qs(environ['QUERY_STRING'])

        # The 'v' parameter in the query string may specify a file version.
        # If none is provided, then '-1' is used, which will return the most
        # recent version.
        version = int(qparams.get('v', [-1])[0])
        try:
            f = self.fs.get_version(path, version)
        except gridfs.errors.NoFile:
            start_response("404 NOT FOUND", [('Content-Type', 'text/plain')])
            return "File not found\n"

        headers = [("Vary", "Accept-Encoding")]

        mimetype, encoding = mimetypes.guess_type(f.name)
        if mimetype:
            headers.append(('Content-Type', mimetype))

        if self._use_gzip(mimetype, environ):
            f = gzip_util.compress(f, self.settings.compression_level)
            headers.append(("Content-Encoding", "gzip"))
        else:
            headers.append(('Content-Length', str(f.length)))

        if self.settings.cache_days is not None:
            expiration = (datetime.now() +
                          timedelta(days=self.settings.cache_days))
            stamp = mktime(expiration.timetuple())
            headers.append(('Expires', format_date_time(stamp)))

        extra_headers = getattr(self.settings, 'extra_headers', None)
        if extra_headers:
            headers.extend(extra_headers.items())

        start_response("200 OK", headers)
        return f

    def _use_gzip(self, mimetype, environ):
        if not mimetype in self.settings.compressable_mimetypes:
            return False

        encode_header = environ.get('HTTP_ACCEPT_ENCODING', '')
        if not gzip_util.gzip_requested(encode_header):
            return False

        return True


def main():

    settings = get_settings()

    print "Connecting to Mongo at %s." % settings.mongo_url
    mongo_parsed = parse_mongo_uri(settings.mongo_url)
    settings.mongo_collection = mongo_parsed['collection']
    c = pymongo.MongoClient(host=settings.mongo_url)
    db = c[mongo_parsed['database']]

    address = settings.host, settings.port
    server = WSGIServer(address, Khartoum(db, settings))
    try:
        print "Khartoum server running on %s:%d. Ctrl+C to quit." % address
        server.serve_forever()
    except KeyboardInterrupt:
        server.stop()
        print "Khartoum server stopped."

if __name__ == '__main__':
    main()
