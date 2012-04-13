import os
import mimetypes
import posixpath

from gevent.wsgi import WSGIServer
from gevent import monkey
import pymongo
import gridfs
import yaml

import gzip_util

# default configuration.  Overridable.
config = {
    'host': 'localhost',
    'port': 8000,
    'mongo_host': 'localhost',
    'mongo_port': '27017',
    'mongo_db': 'test',
    'mongo_collection': 'fs',
}


def read_config():
    # check for APP_SETTINGS_YAML env var and read settings from it if found.
    if 'APP_SETTINGS_YAML' in os.environ:
        config.update(yaml.safe_load(open(os.environ['APP_SETTINGS_YAML'])))
    else:
        # look for a settings.yaml file in cwd
        if os.path.isfile('settings.yaml'):
            config.update(yaml.safe_load(open('settings.yaml')))
    # TODO: read from heroku style env vars as well.


def make_app(db, fs):

    def app(environ, start_response):
        path = environ['PATH_INFO']
        if path.startswith('/'):
            path = path[1:]

        doc = db.fs.files.find_one({'filename':path})

        if not doc:
            start_response("404 NOT FOUND", [('Content-Type', 'text/plain')])
            return "File not found"

        f = fs.get(doc['_id'])
        headers = [("Vary", "Accept-Encoding")]
        mimetype, encoding = mimetypes.guess_type(f.name)

        if mimetype:
            headers.append(('Content-Type', mimetype))

        if gzip_util.client_wants_gzip(environ.get('HTTP_ACCEPT_ENCODING', '')):
            #f = gzip_util.GzipWrap(f, str(posixpath.basename(f.name)))
            f = gzip_util.compress(f, 9)
            headers.append(("Content-Encoding", "gzip"))

        start_response("200 OK", headers)
        return f

    return app


def main():
    monkey.patch_all()

    read_config()

    conn = pymongo.Connection(config['mongo_host'], int(config['mongo_port']))
    db = conn[config['mongo_db']]
    fs = gridfs.GridFS(db, config['mongo_collection'])

    address = config['host'], config['port']
    server = WSGIServer(address, make_app(db, fs))
    try:
        print "Server running on port %s:%d. Ctrl+C to quit" % address
        server.serve_forever()
    except KeyboardInterrupt:
        server.stop()
        print "Bye bye"

if __name__ == '__main__':
    main()
