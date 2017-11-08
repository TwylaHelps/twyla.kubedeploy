import unittest

from twyla.kubedeploy import docker_helpers

class DockerTests(unittest.TestCase):

    def test_make_tag(self):
        tag = docker_helpers.make_tag('myown.private.repo', 'the-service', '678fg')
        assert tag == 'myown.private.repo/the-service:678fg'

    def test_tag_components(self):
        domain, name, version = docker_helpers.tag_components(
            'myown.private.repo/the-service:678fg')
        assert domain == 'myown.private.repo'
        assert name == 'the-service'
        assert version == '678fg'
