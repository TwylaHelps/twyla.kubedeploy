import unittest
from unittest import mock
import json
import base64
from subprocess import PIPE, STDOUT

from twyla.kubedeploy import docker_helpers

DOCKER_CREDENTIALS = "tim_toddler:crappy password"
DOCKER_CONF = json.dumps({
    "auths": {
        "myown.private.registry": {
	    "auth": str(base64.b64encode(DOCKER_CREDENTIALS.encode('utf-8')).decode('utf-8'))
        }
    }
})

MACOS_DOCKER_CONF = json.dumps({
    "auths": {
        "myown.private.registry": {},
    },
    "credsStore": "osxkeychain"
})

class DockerTests(unittest.TestCase):

    def test_make_tag(self):
        tag = docker_helpers.make_tag('myown.private.registry',
                                      'the-service',
                                      '678fg')
        assert tag == 'myown.private.registry/the-service:678fg'


    def test_tag_components(self):
        domain, name, version = docker_helpers.tag_components(
            'myown.private.registry/the-service:678fg')
        assert domain == 'myown.private.registry'
        assert name == 'the-service'
        assert version == '678fg'


    @mock.patch('twyla.kubedeploy.docker_helpers.open',
                new=mock.mock_open(read_data=DOCKER_CONF))
    @mock.patch('twyla.kubedeploy.docker_helpers.registry')
    def test_docker_image_exists(self, mock_registry):
        mock_client = mock_registry.DockerRegistryClient.return_value
        mock_client.repository.return_value.tags.return_value = ['678fg', '123gf']
        exists = docker_helpers.docker_image_exists('myown.private.registry/the-service:678fg')
        assert exists
        mock_registry.DockerRegistryClient.assert_called_once_with(
            "https://myown.private.registry",
            username="tim_toddler",
            password="crappy password")
        mock_client.repository.assert_called_once_with("the-service")


    @mock.patch('twyla.kubedeploy.docker_helpers.open',
                new=mock.mock_open(read_data=DOCKER_CONF))
    @mock.patch('twyla.kubedeploy.docker_helpers.registry')
    def test_docker_image_exists(self, mock_registry):
        mock_client = mock_registry.DockerRegistryClient.return_value
        mock_client.repository.return_value.tags.return_value = ['123gf']
        exists = docker_helpers.docker_image_exists('myown.private.registry/the-service:678fg')
        assert not exists


    @mock.patch('twyla.kubedeploy.docker_helpers.Popen')
    def test_get_macos_credentials(self, mock_popen):
        creds = json.dumps({
            'Username': 'tim_toddler', 'Secret': 'mysecret'
        }).encode('utf-8')
        communicate = mock_popen.return_value.communicate
        communicate.return_value = (creds, None)
        username, secret = docker_helpers.get_macos_credentials('myown.private.registry')
        mock_popen.assert_called_once_with(
            ['docker-credential-osxkeychain', 'get'],
            stdout=PIPE, stdin=PIPE, stderr=STDOUT)
        communicate.assert_called_once_with(input=b'myown.private.registry')
        assert username == 'tim_toddler'
        assert secret == 'mysecret'


    @mock.patch('twyla.kubedeploy.docker_helpers.open',
                new=mock.mock_open(read_data=MACOS_DOCKER_CONF))
    @mock.patch('twyla.kubedeploy.docker_helpers.registry')
    @mock.patch('twyla.kubedeploy.docker_helpers.get_macos_credentials')
    def test_docker_image_exists_on_macos(self, mock_credentials, mock_client):
        mock_credentials.return_value = 'tim_toddler', 'mysecret'
        mock_client.repository.return_value.tags.return_value = ['678fg', '123gf']
        exists = docker_helpers.docker_image_exists(
            'myown.private.registry/the-service:678fg')
        mock_credentials.assert_called_once_with('myown.private.registry')
