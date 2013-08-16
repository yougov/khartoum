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
from pymongo.uri_parser import parse_uri as parse_mongo_uri
import gridfs
import yaml

import gzip_util

def get_config():
    """
    Return necessary configuration.  If APP_SETTINGS_YAML env var is set, that
    file will be read into config.

    If MONGODB_URL env var is set, that will override the config file.

    If PORT env var is set, that will also override the config file.
    """

    # default configuration.  Overridable.
    config = {
        'host': '0.0.0.0',
        'port': 8000,
        'mongo_host': 'localhost',
        'mongo_port': None,
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

    # Additionally, the PORT environment variable will be used if set.
    if 'APP_SETTINGS_YAML' in os.environ:
        config.update(yaml.safe_load(open(os.environ['APP_SETTINGS_YAML'])))

        # If yaml file had MONGODB_URL setting in it, convert that to the
        # config shape we expect
        if 'MONGODB_URL' in config:
            config.update(mongo_uri_to_config(config['MONGODB_URL']))

    elif os.path.isfile('settings.yaml'):
        config.update(yaml.safe_load(open('settings.yaml')))

    # PORT env var overrides settings.yaml
    config['port'] = os.environ.get('PORT', config['port'])


    # MONGODB_URL env var overrides settings.yaml
    mongo_envvar = os.environ.get('MONGODB_URL')
    if mongo_envvar:
        config.update(mongo_uri_to_config(mongo_envvar))

    return config


def mongo_uri_to_config(mongo_uri, defaults=None):
    """
    Given a Mongo DB URL like that expected by pymongo.uri_parser, parse it
    into a dict and convert its keys to match the names used in Khartoum
    config.
    """
    parsed = parse_mongo_uri(mongo_uri)

    return {
        # pymongo.Connection supports just passing in a URI for the host, in
        # which case we should leave port as None
        'mongo_host': mongo_uri,
        'mongo_port': None,
        'mongo_db': parsed['database'],
        'mongo_collection': parsed['collection']
    }


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

        if self.config.get('expires_days') is not None:
            expiration = (datetime.now() +
                          timedelta(days=self.config['expires_days']))
            stamp = mktime(expiration.timetuple())
            headers.append(('Expires', format_date_time(stamp)))

        extra_headers = self.config.get('extra_headers')
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

    config = get_config()

    mongo_port = config['mongo_port']
    conn = pymongo.Connection(
        host=config['mongo_host'],
        port=int(mongo_port) if mongo_port else None
    )

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
