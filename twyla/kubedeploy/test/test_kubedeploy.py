import unittest
from unittest import mock

from twyla import kubedeploy


class KubeTests(unittest.TestCase):

    @mock.patch('twyla.kubedeploy.kube.kubernetes.config')
    @mock.patch('twyla.kubedeploy.kube.kubernetes.client')
    def test_get_deployment_when_exists(self, mock_client, _):
        kube = kubedeploy.Kube('ns', 'api', None, None)
        kube.get_deployment()
        v1_beta = mock_client.ExtensionsV1beta1Api.return_value
        assert v1_beta.read_namespaced_deployment.call_count == 1
        v1_beta.read_namespaced_deployment.assert_called_once_with(
            name='api', namespace='ns')

    # NOTE: will be used once file fallback is in place
    # @mock.patch('twyla.kubedeploy.kube.kubernetes.client.ExtensionsV1beta1Api')
    # def test_get_deployment_missing(self, mock_client):
    #     v1_beta = mock_client.return_value
    #     v1_beta.read_namespaced_deployment.side_effect = ApiException(status=404)
    #     kube = kubedeploy.Kube('ns', 'api', None, None)
    #     with pytest.raises(kubedeploy.KubeException):
    #         kube.get_deployment()
