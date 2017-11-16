import unittest
from unittest import mock

import pytest
from kubernetes.client.rest import ApiException

from twyla import kubedeploy

CONFIG = """
namespace: ns
"""

class LoadOptionsTest(unittest.TestCase):

    @mock.patch('twyla.kubedeploy.open', new=mock.mock_open(read_data=CONFIG))
    @mock.patch('twyla.kubedeploy.os.path.isfile')
    def test_load_options_file(self, mock_isfile):
        mock_isfile.return_value = True
        options = kubedeploy.load_options('/path/to/great-service')
        assert options['namespace'] == 'ns'
        # This is still taken from the default config, and is the
        # name of dir
        assert options['service_name'] == 'great-service'
        mock_isfile.assert_called_once_with('/path/to/great-service/.kubedeploy')


    @mock.patch('twyla.kubedeploy.os.path.isfile')
    def test_default_values_on_missing_options(self, mock_isfile):
        mock_isfile.return_value = False
        options = kubedeploy.load_options('/service/base/path')
        assert options['namespace'] == 'default'
        assert options['service_name'] == 'path'



class KubeTests(unittest.TestCase):

    @mock.patch('twyla.kubedeploy.kube.kubernetes.config')
    @mock.patch('twyla.kubedeploy.kube.kubernetes.client')
    def test_get_deployment_when_exists(self, mock_client, _):
        kube = kubedeploy.Kube('ns', 'api', None, None)
        deployment = kube.get_deployment()
        v1_beta = mock_client.ExtensionsV1beta1Api.return_value
        assert v1_beta.read_namespaced_deployment.call_count == 1
        v1_beta.read_namespaced_deployment.assert_called_once_with(
            name='api', namespace='ns')


    @mock.patch('twyla.kubedeploy.kube.kubernetes.config')
    @mock.patch('twyla.kubedeploy.kube.kubernetes.client.ExtensionsV1beta1Api')
    def test_get_deployment_missing(self, mock_client, _):
        v1_beta = mock_client.return_value
        v1_beta.read_namespaced_deployment.side_effect = ApiException(status=404)
        kube = kubedeploy.Kube('ns', 'api', None, None)
        with pytest.raises(kubedeploy.KubeException) as context:
            deployment = kube.get_deployment()
