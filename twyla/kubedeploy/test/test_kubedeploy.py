import unittest
import unittest.mock as mock

from jinja2 import Template

from twyla.kubedeploy.kube import Kube
from twyla.kubedeploy.kubectl import Kubectl, KubectlCallFailed

TEST_TEMPLATE = '''
apiVersion: extensions/v1beta1 # for versions since 1.8.0 use apps/v1beta2
kind: Deployment
metadata:
  name: {{ data.name }}
  labels:
    app: {{ data.name }}
spec:
  replicas: {{ data.replicas if data.replicas else 2 }}
  selector:
    matchLabels:
      app: {{ data.name }}
  template:
    metadata:
      labels:
        app: {{ data.name }}
    spec:
      containers:
      - name: {{ data.name }}
        image: {{ data.image }}
        ports:
        - containerPort: 80
'''


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


    @mock.patch('twyla.kubedeploy.kube.Kube.get_remote_deployment')
    @mock.patch('twyla.kubedeploy.kube.Environment.get_template')
    def test_render_template(self, mock_template, mock_deployment):
        mock_template.return_value = Template(TEST_TEMPLATE)
        mock_deployment.return_value = {
            'spec': {
                'replicas': 2
            },
            'status': {
                'replicas': 15
            }
        }

        kube = Kube(
            namespace='test-space',
            deployment_name='test-ployment',
            printer=mock.MagicMock(),
            error_printer=mock.MagicMock()
        )
        file_name = kube.render_template('myreg/myimage:ver001')

        with open(file_name) as fd:
            content = fd.read()

        expected = '''
apiVersion: extensions/v1beta1 # for versions since 1.8.0 use apps/v1beta2
kind: Deployment
metadata:
  name: test-ployment
  labels:
    app: test-ployment
spec:
  replicas: 15
  selector:
    matchLabels:
      app: test-ployment
  template:
    metadata:
      labels:
        app: test-ployment
    spec:
      containers:
      - name: test-ployment
        image: myreg/myimage:ver001
        ports:
        - containerPort: 80'''

        assert content == expected


    @mock.patch('twyla.kubedeploy.kube.Kube.get_remote_deployment')
    @mock.patch('twyla.kubedeploy.kube.Environment.get_template')
    def test_render_template_failed_remote(self, mock_template,
                                           mock_deployment):
        def raiser():
            raise KubectlCallFailed(b'Failed Call!!!')

        mock_template.return_value = Template(TEST_TEMPLATE)
        mock_deployment.side_effect = raiser
        error_printer = mock.MagicMock()
        kube = Kube(
            namespace='test-space',
            deployment_name='test-ployment',
            printer=mock.MagicMock(),
            error_printer=error_printer
        )
        file_name = kube.render_template('myreg/myimage:ver001')

        with open(file_name) as fd:
            content = fd.read()

        error_printer.assert_called_once_with('Failed Call!!!')

        expected = '''
apiVersion: extensions/v1beta1 # for versions since 1.8.0 use apps/v1beta2
kind: Deployment
metadata:
  name: test-ployment
  labels:
    app: test-ployment
spec:
  replicas: 2
  selector:
    matchLabels:
      app: test-ployment
  template:
    metadata:
      labels:
        app: test-ployment
    spec:
      containers:
      - name: test-ployment
        image: myreg/myimage:ver001
        ports:
        - containerPort: 80'''

        assert content == expected


    def test_print_deployment_info(self):
        deployment = {
            'spec': {
                'template': {
                    'spec': {
                        'containers': [{
                            'image': 'my-test-image:ver002'
                        }]
                    }
                }
            },
            'status': {
                'replicas': 4,
                'readyReplicas': 3
            }
        }
        printer = mock.MagicMock()

        kube = Kube(
            namespace='test-space',
            deployment_name='test-ployment',
            printer=printer,
            error_printer=mock.MagicMock()
        )

        kube.print_deployment_info('tester', deployment)

        assert printer.call_count == 3
        (one, two, three) = printer.call_args_list
        assert one == mock.call('tester:')
        assert two == mock.call('image: my-test-image:ver002')
        assert three == mock.call('    replicas: 3/4')


    @mock.patch('twyla.kubedeploy.kube.Kube.print_deployment_info')
    @mock.patch('twyla.kubedeploy.kube.Kube.get_remote_deployment')
    def test_info(self, mock_remote, mock_printer):
        deployment = {
            'spec': {
                'template': {
                    'spec': {
                        'containers': [{
                            'image': 'my-test-image:ver002'
                        }]
                    }
                }
            },
            'status': {
                'replicas': 4,
                'readyReplicas': 3
            }
        }
        mock_remote.return_value = deployment

        kube = Kube(
            namespace='test-space',
            deployment_name='test-ployment',
            printer=mock.MagicMock(),
            error_printer=mock.MagicMock()
        )
        kube.info()
        mock_printer.assert_called_once_with('Current test-ployment',
                                             deployment)


    @mock.patch('twyla.kubedeploy.kube.Kube.get_remote_deployment')
    def test_info_failed_remote(self, mock_remote):
        def raiser():
            raise KubectlCallFailed(b'Failed Call!!!')

        mock_remote.side_effect = raiser
        error_printer = mock.MagicMock()

        kube = Kube(
            namespace='test-space',
            deployment_name='test-ployment',
            printer=mock.MagicMock(),
            error_printer=error_printer
        )
        kube.info()
        error_printer.assert_called_once_with('Failed Call!!!')


    @mock.patch('twyla.kubedeploy.kube.Kube.render_template')
    @mock.patch('twyla.kubedeploy.kube.Kubectl.apply')
    def test_apply(self, mock_apply, mock_render):
        mock_render.return_value = '/a/file/path'
        mock_apply.return_value = 'some\napply\noutput'
        mock_printer = mock.MagicMock()

        kube = Kube(
            namespace='test-space',
            deployment_name='test-ployment',
            printer=mock_printer,
            error_printer=mock.MagicMock()
        )
        kube.apply('my-reg/my-test-image:ver123')

        mock_render.assert_called_once_with('my-reg/my-test-image:ver123')
        assert mock_printer.call_count == 3
        (one, two, three) = mock_printer.call_args_list
        assert one == mock.call('some')
        assert two == mock.call('apply')
        assert three == mock.call('output')
