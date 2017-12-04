import json
import unittest
from unittest import mock

import kubernetes
import pytest
import yaml
from kubernetes.client.rest import ApiException
from twyla.kubedeploy import kube


DEPLOYMENT = """
apiVersion: apps/v1beta1 # for versions since 1.8.0 use apps/v1beta2
kind: Deployment
metadata:
  name: nginx-deployment
  labels:
    app: nginx
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.7.9
        ports:
        - containerPort: 80
"""

DEPLOYMENT_WITH_REPLICAS = """
{deployment}
status:
  replicas: 4
  ready_replicas: 3
""".format(deployment=DEPLOYMENT)

SERVICE = """
kind: Service
apiVersion: v1
metadata:
  name: my-service
spec:
  selector:
    app: MyApp
  ports:
  - protocol: TCP
    port: 80
    targetPort: 9376
"""

MULTIDOC = """
---
{deployment}
---
{service}
""".format(service=SERVICE, deployment=DEPLOYMENT)

MULTIMULTIDOC = """
---
{deployment}
---
{deployment}
""".format(deployment=DEPLOYMENT)

TOOMANY = """
---
{deployment}
---
{deployment}
---
{service}
---
{service}
""".format(service=SERVICE, deployment=DEPLOYMENT)


class KubeTests(unittest.TestCase):
    @mock.patch('twyla.kubedeploy.kube.kubernetes.config')
    def test_type_name_from_data(self, _):
        data = yaml.load(DEPLOYMENT)
        kub = kube.Kube('ns', 'api', None, None)
        type_name = kub.type_name_from_data(data)
        # Assert some basics that hint on success
        assert type_name == 'AppsV1beta1Deployment'


    @mock.patch('twyla.kubedeploy.kube.kubernetes.config')
    def test_parse_deployment_data(self, _):
        data = yaml.load(DEPLOYMENT)
        kub = kube.Kube('ns', 'api', None, None)
        res = kub.parse_data(data)
        # Assert some basics that hint on success
        assert isinstance(res, kubernetes.client.AppsV1beta1Deployment)
        assert res.kind == 'Deployment'
        assert len(res.spec.template.spec.containers) == 1
        assert res.spec.template.spec.containers[0].name == 'nginx'


    @mock.patch('twyla.kubedeploy.kube.kubernetes.config')
    def test_parse_deployment_data(self, _):
        data = yaml.load(DEPLOYMENT)
        kub = kube.Kube('ns', 'api', None, None)
        res = kub.parse_data(data)
        # Assert some basics that hint on success
        assert isinstance(res, kubernetes.client.AppsV1beta1Deployment)
        assert res.kind == 'Deployment'
        assert len(res.spec.template.spec.containers) == 1
        assert res.spec.template.spec.containers[0].name == 'nginx'


    @mock.patch('twyla.kubedeploy.kube.kubernetes.config')
    def test_parse_service_data(self, _):
        data = yaml.load(SERVICE)
        kub = kube.Kube('ns', 'api', None, None)
        res = kub.parse_data(data)
        # Assert some basics that hint on success
        assert isinstance(res, kubernetes.client.V1Service)
        assert res.kind == 'Service'
        assert len(res.spec.ports) == 1
        assert res.spec.ports[0].target_port == '9376'


    @mock.patch('twyla.kubedeploy.kube.open',
                new=mock.mock_open(read_data=MULTIDOC))
    @mock.patch('twyla.kubedeploy.kube.kubernetes.config')
    def test_load_objects_from_file(self, _):
        kub = kube.Kube('ns', 'api', None, None)
        kub.load_objects_from_file()
        # Assert some basics that hint on success
        assert len(kub.objects) == 2

        res = kub.objects.get_deployment()
        assert isinstance(res, kubernetes.client.AppsV1beta1Deployment)
        assert res.kind == 'Deployment'
        assert len(res.spec.template.spec.containers) == 1
        assert res.spec.template.spec.containers[0].name == 'nginx'

        res = kub.objects.get_service()
        assert isinstance(res, kubernetes.client.V1Service)
        assert res.kind == 'Service'
        assert len(res.spec.ports) == 1
        assert res.spec.ports[0].target_port == '9376'


    @mock.patch('twyla.kubedeploy.kube.open',
                new=mock.mock_open(read_data=''))
    @mock.patch('twyla.kubedeploy.kube.kubernetes.config')
    def test_load_objects_from_not_found(self, _):
        kub = kube.Kube('ns', 'api', None, None)
        kub.load_objects_from_file()
        # Assert some basics that hint on success
        assert len(kub.objects) == 0

        with pytest.raises(kube.DeploymentNotFoundException):
            kub.objects.get_deployment()

        with pytest.raises(kube.ServiceNotFoundException):
            kub.objects.get_service()


    @mock.patch('twyla.kubedeploy.kube.open',
                new=mock.mock_open(read_data=TOOMANY))
    @mock.patch('twyla.kubedeploy.kube.kubernetes.config')
    def test_load_objects_from_multi(self, _):
        kub = kube.Kube('ns', 'api', None, None)
        kub.load_objects_from_file()
        # Assert some basics that hint on success
        assert len(kub.objects) == 4

        with pytest.raises(kube.MultipleDeploymentDefinitionsException):
            kub.objects.get_deployment()

        with pytest.raises(kube.MultipleServicesDefinitionsException):
            kub.objects.get_service()


    @mock.patch('twyla.kubedeploy.kube.open',
                new=mock.mock_open(read_data=DEPLOYMENT))
    @mock.patch('twyla.kubedeploy.kube.kubernetes.config')
    def test_load_deployment_form_file(self, _):
        kub = kube.Kube('ns', 'api', None, None)
        res = kub.load_deployment_from_file()
        # Assert some basics that hint on success
        assert isinstance(res, kubernetes.client.AppsV1beta1Deployment)
        assert res.kind == 'Deployment'
        assert len(res.spec.template.spec.containers) == 1
        assert res.spec.template.spec.containers[0].name == 'nginx'


    @mock.patch('twyla.kubedeploy.kube.open',
                new=mock.mock_open(read_data=MULTIDOC))
    @mock.patch('twyla.kubedeploy.kube.kubernetes.config')
    def test_load_multidoc_form_file(self, _):
        kub = kube.Kube('ns', 'api', None, None)
        res = kub.load_deployment_from_file()
        # Assert some basics that hint on success
        assert isinstance(res, kubernetes.client.AppsV1beta1Deployment)
        assert res.kind == 'Deployment'
        assert len(res.spec.template.spec.containers) == 1
        assert res.spec.template.spec.containers[0].name == 'nginx'


    @mock.patch('twyla.kubedeploy.kube.open',
                new=mock.mock_open(read_data=MULTIMULTIDOC))
    @mock.patch('twyla.kubedeploy.kube.kubernetes.config')
    def test_load_too_many_deployments_form_file(self, _):
        kub = kube.Kube('ns', 'api', None, None)
        with pytest.raises(kube.MultipleDeploymentDefinitionsException):
            kub.load_deployment_from_file()

    @mock.patch('twyla.kubedeploy.kube.open',
                new=mock.mock_open(read_data='---'))
    @mock.patch('twyla.kubedeploy.kube.kubernetes.config')
    def test_load_no_deployments_form_file(self, _):
        kub = kube.Kube('ns', 'api', None, None)
        with pytest.raises(kube.DeploymentNotFoundException):
            kub.load_deployment_from_file()

    @mock.patch('twyla.kubedeploy.kube.kubernetes.config')
    @mock.patch('twyla.kubedeploy.kube.kubernetes.client')
    def test_get_deployment_when_exists(self, mock_client, _):
        kub = kube.Kube('ns', 'api', None, None)
        kub.get_deployment()
        v1_beta = mock_client.AppsV1beta1Api.return_value
        assert v1_beta.read_namespaced_deployment.call_count == 1
        v1_beta.read_namespaced_deployment.assert_called_once_with(
            name='api', namespace='ns')


    @mock.patch('twyla.kubedeploy.kube.kubernetes.config')
    @mock.patch('twyla.kubedeploy.kube.kubernetes.client.AppsV1beta1Api')
    def test_get_deployment_missing(self, mock_client, _):
        v1_beta = mock_client.return_value
        v1_beta.read_namespaced_deployment.side_effect = ApiException(status=404)
        kub = kube.Kube('ns', 'api', None, None)
        with pytest.raises(kube.DeploymentNotFoundException):
            kub.get_deployment()


    @mock.patch('twyla.kubedeploy.kube.kubernetes.config')
    @mock.patch('twyla.kubedeploy.kube.kubernetes.client.AppsV1beta1Api')
    def test_get_deployment_rethrow(self, mock_client, _):
        v1_beta = mock_client.return_value
        v1_beta.read_namespaced_deployment.side_effect = ApiException(status=503)
        kub = kube.Kube('ns', 'api', None, None)
        with pytest.raises(ApiException):
            kub.get_deployment()


    @mock.patch('twyla.kubedeploy.kube.open',
                new=mock.mock_open(read_data=DEPLOYMENT))
    @mock.patch('twyla.kubedeploy.kube.kubernetes.config')
    @mock.patch('twyla.kubedeploy.kube.kubernetes.client.AppsV1beta1Api')
    def test_deployment_new(self, mock_client, _):
        v1_beta = mock_client.return_value
        v1_beta.read_namespaced_deployment.side_effect = ApiException(status=404)

        kub = kube.Kube('ns', 'api', mock.MagicMock(), mock.MagicMock())
        expected = kub.fill_deployment_definition(
            kub.load_deployment_from_file(), 'myreg/test-service:version')

        kub.deploy('myreg/test-service:version')
        v1_beta.create_namespaced_deployment.assert_called_once_with(
            namespace='ns', body=expected)


    @mock.patch('twyla.kubedeploy.kube.open',
                new=mock.mock_open(read_data=DEPLOYMENT))
    @mock.patch('twyla.kubedeploy.kube.kubernetes.config')
    @mock.patch('twyla.kubedeploy.kube.kubernetes.client.AppsV1beta1Api')
    def test_deployment_exists(self, mock_client, _):
        v1_beta = mock_client.return_value
        v1_beta.read_namespaced_deployment.return_value = 'some_deployment'

        kub = kube.Kube('ns', 'api', mock.MagicMock(), mock.MagicMock())
        expected = kub.fill_deployment_definition(
            kub.load_deployment_from_file(), 'myreg/test-service:version')

        kub.deploy('myreg/test-service:version')
        v1_beta.patch_namespaced_deployment.assert_called_once_with(
            name='api', namespace='ns', body=expected)


    @mock.patch('twyla.kubedeploy.kube.open',
                new=mock.mock_open(read_data=DEPLOYMENT))
    @mock.patch('twyla.kubedeploy.kube.kubernetes.config')
    @mock.patch('twyla.kubedeploy.kube.kubernetes.client.AppsV1beta1Api')
    def test_deployment_api_exception(self, mock_client, _):
        v1_beta = mock_client.return_value
        v1_beta.read_namespaced_deployment.side_effect = ApiException(status=503)

        errors = mock.MagicMock()
        kub = kube.Kube('ns', 'api', mock.MagicMock(), errors)
        kub.deploy('myreg/test-service:version')

        assert errors.call_count == 1
        (got) = errors.call_args[0][0]
        assert isinstance(got, ApiException)


    @mock.patch('twyla.kubedeploy.kube.open',
                new=mock.mock_open(read_data=MULTIMULTIDOC))
    @mock.patch('twyla.kubedeploy.kube.kubernetes.config')
    @mock.patch('twyla.kubedeploy.kube.kubernetes.client.AppsV1beta1Api')
    def test_deployment_too_many_deployments(self, mock_client, _):
        errors = mock.MagicMock()
        kub = kube.Kube('ns', 'api', mock.MagicMock(), errors)
        kub.deploy('myreg/test-service:version')

        assert errors.call_count == 1
        (got) = errors.call_args[0][0]
        assert got == 'Only one deployment is currently allowed in deployment.yml'

        mock_client.assert_called_once_with()


    @mock.patch('twyla.kubedeploy.kube.open',
                new=mock.mock_open(read_data='---'))
    @mock.patch('twyla.kubedeploy.kube.kubernetes.config')
    @mock.patch('twyla.kubedeploy.kube.kubernetes.client.AppsV1beta1Api')
    def test_deployment_no_deployments(self, mock_client, _):
        errors = mock.MagicMock()
        kub = kube.Kube('ns', 'api', mock.MagicMock(), errors)
        kub.deploy('myreg/test-service:version')

        assert errors.call_count == 1
        (got) = errors.call_args[0][0]
        assert got == 'No deployment definition found in deployment.yml'

        mock_client.assert_called_once_with()


    @mock.patch('twyla.kubedeploy.kube.open',
                new=mock.mock_open(read_data=DEPLOYMENT))
    @mock.patch('twyla.kubedeploy.kube.kubernetes.config')
    @mock.patch('twyla.kubedeploy.kube.Kube.get_deployment')
    @mock.patch('twyla.kubedeploy.kube.Kube.print_deployment_info')
    def test_info(self, mock_print_info, mock_get_deployment, _):
        kub = kube.Kube('ns', 'api', mock.MagicMock(), mock.MagicMock())
        deployment = kub.load_deployment_from_file()
        mock_get_deployment.return_value = deployment
        kub.info()

        mock_print_info.assert_called_once_with('Current api', deployment)


    @mock.patch('twyla.kubedeploy.kube.kubernetes.config')
    @mock.patch('twyla.kubedeploy.kube.Kube.get_deployment')
    @mock.patch('twyla.kubedeploy.kube.Kube.print_deployment_info')
    def test_info_not_found(self, mock_print_info, mock_get_deployment, _):
        errors = mock.MagicMock()
        kub = kube.Kube('ns', 'api', mock.MagicMock(), errors)
        mock_get_deployment.side_effect = kube.DeploymentNotFoundException(
            'not found')
        kub.info()

        mock_print_info.assert_not_called()
        assert errors.call_count == 1
        (got) = errors.call_args[0][0]
        assert isinstance(got, kube.DeploymentNotFoundException)


    @mock.patch('twyla.kubedeploy.kube.open',
                new=mock.mock_open(read_data=DEPLOYMENT))
    @mock.patch('twyla.kubedeploy.kube.Kube.get_deployment')
    @mock.patch('twyla.kubedeploy.kube.kubernetes.config')
    def test_print_deployment_info(self, _, __):
        errors = mock.MagicMock()
        printer = mock.MagicMock()
        kub = kube.Kube('ns', 'api', printer, errors)
        deployment = kub.load_deployment_from_file()

        kub.print_deployment_info(title='a title', deployment=deployment)

        printer.assert_has_calls([
            mock.call('a title:'),
            mock.call('image: nginx:1.7.9', 4),
            mock.call('replicas: no deployment', 4)
        ])


    @mock.patch('twyla.kubedeploy.kube.open',
                new=mock.mock_open(read_data=DEPLOYMENT_WITH_REPLICAS))
    @mock.patch('twyla.kubedeploy.kube.Kube.get_deployment')
    @mock.patch('twyla.kubedeploy.kube.kubernetes.config')
    def test_print_deployment_info_with_replicas(self, _, __):
        errors = mock.MagicMock()
        printer = mock.MagicMock()
        kub = kube.Kube('ns', 'api', printer, errors)
        deployment = kub.load_deployment_from_file()
        deployment.status.replicas = 4
        deployment.status.ready_replicas = 3

        kub.print_deployment_info(title='a title', deployment=deployment)

        printer.assert_has_calls([
            mock.call('a title:'),
            mock.call('image: nginx:1.7.9', 4),
            mock.call('replicas: 3/4', 4)
        ])


    @mock.patch('twyla.kubedeploy.kube.open',
                new=mock.mock_open(read_data=DEPLOYMENT))
    @mock.patch('twyla.kubedeploy.kube.Kube.get_deployment')
    @mock.patch('twyla.kubedeploy.kube.kubernetes.config')
    def test_print_deployment_info_none(self, _, __):
        errors = mock.MagicMock()
        printer = mock.MagicMock()
        kub = kube.Kube('ns', 'api', printer, errors)
        deployment = kub.load_deployment_from_file()
        deployment.spec = None

        kub.print_deployment_info(title='a title', deployment=deployment)

        printer.assert_has_calls([
            mock.call('??? is not deployed.')
        ])
