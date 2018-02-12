import unittest
import unittest.mock as mock

from twyla.kubedeploy.kube import Kube
from twyla.kubedeploy.kubectl import Kubectl


class KubeTests(unittest.TestCase):
    def setUp(self):
        self.namespace = 'test-space'
        self.deployment_name = 'test-deployment'
        self.printer = mock.MagicMock()
        self.error_printer = mock.MagicMock()

    def test_init(self):

        kube = Kube(
            namespace=self.namespace,
            printer=self.printer,
            error_printer=self.error_printer,
            deployment_name=self.deployment_name,
        )

        assert isinstance(kube.kubectl, Kubectl)
        assert kube.kubectl.namespace == self.namespace
        assert kube.deployment_template == 'deployment.yml'
        assert kube.printer == self.printer
        assert kube.error_printer == self.error_printer


    @mock.patch('twyla.kubedeploy.kube.Kubectl')
    def test_get_remote_deployment(self, mock_kubectl):
        kube = Kube(
            namespace=self.namespace,
            printer=self.printer,
            error_printer=self.error_printer,
            deployment_name=self.deployment_name,
        )

        expected_res = {'spec': {}, 'metadata': {}}
        mk = mock_kubectl.return_value
        mk.get_deployment.return_value = expected_res

        res = kube.get_remote_deployment()

        assert res == expected_res
        mk.get_deployment.assert_called_once_with(self.deployment_name)
