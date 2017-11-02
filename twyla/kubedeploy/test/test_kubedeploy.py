import unittest
from unittest import mock
from twyla import kubedeploy

CONFIG = """
namespace: ns
"""

class LoadOptionsTest(unittest.TestCase):

    @mock.patch('twyla.kubedeploy.open', new=mock.mock_open(read_data=CONFIG))
    @mock.patch('twyla.kubedeploy.os.path.isfile')
    def test_load_options_file(self, mock_isfile):
        mock_isfile.return_value = True
        options = kubedeploy.load_options('/service/base/path')
        assert options['namespace'] == 'ns'
        mock_isfile.assert_called_once_with('/service/base/path/.kubedeploy')

    @mock.patch('twyla.kubedeploy.os')
    def test_default_values_on_missing_options(self, mock_os):
        mock_os.path.isfile.return_value = False
        options = kubedeploy.load_options('/service/base/path')
        assert options['namespace'] == 'default'


class KubeTests(unittest.TestCase):

    @mock.patch('twyla.kubedeploy.kubernetes.config')
    @mock.patch('twyla.kubedeploy.kubernetes.client')
    def test_get_deployment_when_exists(self, mock_client, _):
        kube = kubedeploy.Kube('ns', 'api', None, None)
        deployment = kube.get_deployment()
        v1_beta = mock_client.ExtensionsV1beta1Api.return_value
        assert v1_beta.read_namespaced_deployment.call_count == 1
        v1_beta.read_namespaced_deployment.assert_called_once_with(
            name='api', namespace='ns')
