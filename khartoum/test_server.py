import sys
import functools

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
