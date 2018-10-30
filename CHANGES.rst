v2.1.0
======

#2: Use gzip compress function from `cherrypy
<https://cherrypy.org>`_ instead of keeping
a local fork of old code.

#1: Incorporate fix from v1.2.1.

v2.0.0
======

Dropped support for Python 3.5 and earlier.

v1.2.1
======

#1: Fix TypeError on Python 3 in gzip handler.

v1.2.0
======

Ensure options such as readPreference, if included in the URL,
are honored by the MongoClient.

v1.1.0
======

Python 3 support.
Basic test suite and CI config.
