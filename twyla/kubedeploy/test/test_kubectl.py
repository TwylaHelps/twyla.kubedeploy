import pytest
import subprocess
import unittest
import unittest.mock as mock

from twyla.kubedeploy.kubectl import Kubectl, KubectlCallFailed


class KubectlTest(unittest.TestCase):
    def test_default_command(self):
        kubectl = Kubectl()

        default_cmd = kubectl._make_command()
        expected = ['kubectl', 'get', 'pods']

        assert default_cmd == expected


    def test_namespaced_command(self):
        kubectl = Kubectl()
        kubectl.namespace = 'twyla'

        default_cmd = kubectl._make_command()
        expected = ['kubectl',
                    '--namespace',
                    'twyla',
                    'get',
                    'pods']

        assert default_cmd == expected


    @mock.patch('twyla.kubedeploy.kubectl.subprocess')
    @mock.patch('twyla.kubedeploy.kubectl.json')
    def test_call(self, mock_json, mock_subprocess):
        mock_pipe = mock.MagicMock()
        mock_subprocess.PIPE = mock_pipe
        kubectl = Kubectl()
        cmd = ['kubectl', 'get', 'pods']
        kubectl._call(cmd)

        mock_subprocess.run.assert_called_once_with(
            cmd,
            stdout=mock_pipe,
            stderr=mock_pipe)


    def test_failing_call(self):
        kubectl = Kubectl()
        cmd = ['ls', '-l', '/does/probably/not/exist']
        with pytest.raises(KubectlCallFailed) as error:
            kubectl._call(cmd)

        assert error.value.args[0] == (b"ls: cannot access "
                                       b"'/does/probably/not/exist': "
                                       b"No such file or directory\n")

    @mock.patch('twyla.kubedeploy.kubectl.subprocess')
    @mock.patch('twyla.kubedeploy.kubectl.json')
    def test_apply(self, mock_json, mock_subprocess):
        mock_pipe = mock.MagicMock()
        mock_subprocess.PIPE = mock_pipe
        kubectl = Kubectl()
        file_name = 'deployment.yml'
        expected = ['kubectl', 'apply', '-f', file_name]

        kubectl.apply(file_name)

        mock_subprocess.run.assert_called_once_with(
            expected,
            stdout=mock_pipe,
            stderr=mock_pipe)


    @mock.patch('twyla.kubedeploy.kubectl.Kubectl._call')
    def test_get_deployment(self, mock_call):
        name = 'test-deployment'
        expected = ['get', 'deployment', name, '-o', 'json']
        expected_call = ['kubectl', '--namespace', 'test-space']
        expected_call.extend(expected)
        kubectl = Kubectl()
        kubectl.namespace = 'test-space'
        kubectl.get_deployment(name)

        assert kubectl.args == expected
        mock_call.assert_called_once_with(expected_call)


    @mock.patch('twyla.kubedeploy.kubectl.Kubectl._call')
    def test_list_deployments(self, mock_call):
        expected = ['get', 'deployments', '-o', 'json']
        expected_call = ['kubectl', '--namespace', 'test-space']
        expected_call.extend(expected)
        kubectl = Kubectl()
        kubectl.namespace = 'test-space'
        kubectl.list_deployments()

        assert kubectl.args == expected
        mock_call.assert_called_once_with(expected_call)
