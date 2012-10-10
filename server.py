import os
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
import gridfs
import yaml

import gzip_util

# default configuration.  Overridable.
config = {
    'host': '0.0.0.0',
    'port': 8000,
    'mongo_host': 'localhost',
    'mongo_port': '27017',
    'mongo_db': 'test',
    'mongo_collection': 'fs',
    # There's little point compressing pngs, jpgs, tar.gz files, etc, and it's
    # really slow, so save compression for the file types where it pays off.
    'compressable_mimetypes': [
        'text/plain',
        'text/html',
        'application/javascript',
        'text/css',
    ],
    'compression_level': 6,  # gzip compression level.  An int from 1-9
    'expires_days': 365,  # Long live the caches!
}


def read_config():
    # Default settings are stored in the 'config' dict in this module.  The
    # defaults may be overridden by passing in an APP_SETTINGS_YAML environment
    # variable that points to a yaml file on disk, or by putting a
    # 'settings.yaml' file in the current working directory.

    # Additionally, the PORT environment variable will be used if set.
    if 'APP_SETTINGS_YAML' in os.environ:
        config.update(yaml.safe_load(open(os.environ['APP_SETTINGS_YAML'])))
    elif os.path.isfile('settings.yaml'):
        config.update(yaml.safe_load(open('settings.yaml')))

    config['port'] = os.environ.get('PORT', config['port'])
    # TODO: read from heroku style env vars as well.


class Khartoum(object):
    def __init__(self, db, app_config):
        self.db = db
        self.config = app_config
        self.fs = gridfs.GridFS(db, self.config['mongo_collection'])

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
            f = gzip_util.compress(f, self.config['compression_level'])
            headers.append(("Content-Encoding", "gzip"))
        else:
            headers.append(('Content-Length', str(f.length)))

        if config.get('expires_days') is not None:
            expiration = (datetime.now() +
                          timedelta(days=config['expires_days']))
            stamp = mktime(expiration.timetuple())
            headers.append(('Expires', format_date_time(stamp)))

        extra_headers = config.get('extra_headers')
        if extra_headers:
            headers.extend(extra_headers.items())

        start_response("200 OK", headers)
        return f

    def _use_gzip(self, mimetype, environ):
        if not mimetype in self.config['compressable_mimetypes']:
            return False

        encode_header = environ.get('HTTP_ACCEPT_ENCODING', '')
        if not gzip_util.gzip_requested(encode_header):
            return False

        return True


def main():

    read_config()

    conn = pymongo.Connection(config['mongo_host'], int(config['mongo_port']))
    db = conn[config['mongo_db']]

    address = config['host'], int(config['port'])
    server = WSGIServer(address, Khartoum(db, config))
    try:
        print "Server running on port %s:%d. Ctrl+C to quit" % address
        server.serve_forever()
    except KeyboardInterrupt:
        server.stop()
        print "Bye bye"

if __name__ == '__main__':
    main()
