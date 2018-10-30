import io
import sys
import functools

import six

import pytest
import requests_toolbelt.sessions
import portend
import munch
from jaraco.mongodb import helper


def port_is_occupied(port):
	try:
		portend.occupied('localhost', port, timeout=0.1)
	except portend.Timeout:
		return False
	return True


@pytest.fixture(scope='session')
def khartoum_instance(mongodb_instance, watcher_getter, request):
	port = portend.find_available_local_port()
	mongo_url = mongodb_instance.get_uri() + '/khartoum.fs'
	service = watcher_getter(
		name=sys.executable,
		arguments=[
			'-m', 'khartoum',
			'--port', str(port),
			'--mongo_url', mongo_url,
		],
		checker=functools.partial(port_is_occupied, port),
		request=request,
	)
	url = 'http://localhost:{port}'.format(**locals())
	session = requests_toolbelt.sessions.BaseUrlSession(url)
	return munch.Munch(locals())


def test_root_is_404(khartoum_instance):
	inst = khartoum_instance
	resp = inst.session.get('/')
	assert resp.status_code == 404


def test_upload_retrieve(khartoum_instance):
	inst = khartoum_instance
	fs = helper.connect_gridfs(inst.mongo_url)
	path = 'tests/test_server.py'
	with open(__file__, 'rb') as infile:
		fs.put(infile, filename=path)
	resp = inst.session.get(path)
	resp.raise_for_status()


def test_upload_retrieve_binary(khartoum_instance):
	"""
	What about a binary file
	"""
	binfile = io.BytesIO(b''.join(map(six.int2byte, range(256))))
	inst = khartoum_instance
	path = 'test/file.bin'
	fs = helper.connect_gridfs(inst.mongo_url)
	fs.put(binfile, filename=path)
	resp = inst.session.get(path)
	resp.raise_for_status()
	assert resp.content == binfile.getvalue()


def test_upload_retrieve_compressable(khartoum_instance):
	"""
	HTML is compressable
	"""
	binfile = io.BytesIO(b'<html>hello world</html>')
	inst = khartoum_instance
	path = 'test/hello.html'
	fs = helper.connect_gridfs(inst.mongo_url)
	fs.put(binfile, filename=path)
	resp = inst.session.get(path)
	resp.raise_for_status()
	assert resp.headers['Content-Encoding'] == 'gzip'
	assert resp.content == binfile.getvalue()
