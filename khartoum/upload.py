import os
import argparse
import warnings

import pymongo.uri_parser
import gridfs


def mongodb_gridfs(uri):
    params = pymongo.uri_parser.parse_uri(uri)
    # Suppress warnings when we pass a URI to MongoDB that includes the
    #  database name.
    warnings.filterwarnings(
        'ignore', category=UserWarning,
        message="must provide a username",
        module='pymongo.connection')
    conn = pymongo.Connection(uri)
    database_name = params['database'] or 'khartoum'
    return gridfs.GridFS(
        conn[database_name], params['collection'] or 'fs')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file')
    parser.add_argument(
        '--uri', dest='store', type=mongodb_gridfs,
        default=mongodb_gridfs('mongodb://localhost'),
        help="The URI for the store. Defaults to "
        "mongodb://localhost/khartoum.fs",
    )
    parser.add_argument(
        '--prefix',
        help="A prefix for the filename (like 'foo/bar/')",
        default='',
    )
    args = parser.parse_args()

    with open(args.input_file, 'rb') as infile:
        filename = os.path.basename(args.input_file)
        args.store.put(infile, filename=args.prefix + filename)


if __name__ == '__main__':
    main()
