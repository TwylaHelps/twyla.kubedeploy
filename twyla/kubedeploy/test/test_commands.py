import os
import tempfile
import traceback
import unittest
from unittest import mock

from click.testing import CliRunner

from twyla import kubedeploy

REQUIREMENTS = '''
some_package==1.2.3
another_package==3.2.1
git+ssh://git_package==0.0.1
'''


class DeployCommandTests(unittest.TestCase):

    @mock.patch('twyla.kubedeploy.docker_helpers.docker_image_exists')
    @mock.patch('twyla.kubedeploy.Kube')
    @mock.patch('twyla.kubedeploy.head_of')
    def test_deploy_master_head(self, mock_head_of, mock_Kube,
                                mock_docker_exists):
        """When passed no arguments, the deploy command deploys head of
        master"""
        mock_head_of.return_value = 'githash'
        mock_docker_exists.return_value = True
        runner = CliRunner()
        result = runner.invoke(kubedeploy.deploy, ['--registry',
                                                   'myown.private.registry',
                                                   '--image',
                                                   'test-service',
                                                   '--name',
                                                   'test-deployment',
                                                   '--namespace',
                                                   'anamespace'])
        if result.exception:
            print(''.join(traceback.format_exception(*result.exc_info)))
            self.fail()

        # Default branch is master, and local is False
        mock_head_of.assert_called_once_with(os.getcwd(),
                                             'master',
                                             local=False)
        mock_Kube.assert_called_once_with(
            namespace='anamespace',
            deployment_name='test-service',
            printer=kubedeploy.prompt,
            error_printer=kubedeploy.error_prompt)
        kube = mock_Kube.return_value
        kube.apply.assert_called_once_with(
            'myown.private.registry/test-service:githash'
        )


    @mock.patch('twyla.kubedeploy.docker_helpers.docker_image')
    @mock.patch('twyla.kubedeploy.docker_helpers.docker_image_exists')
    @mock.patch('twyla.kubedeploy.Kube')
    @mock.patch('twyla.kubedeploy.head_of')
    def test_deploy_local_head(self, mock_head_of, mock_Kube,
                               mock_docker_exists, mock_docker_image):
        """When passed the local flag, the deploy command deploys head of the
        local git state"""
        mock_head_of.return_value = 'githash'
        mock_docker_exists.return_value = True
        runner = CliRunner()
        result = runner.invoke(kubedeploy.deploy, ['--registry',
                                                   'myown.private.registry',
                                                   '--image',
                                                   'test-service',
                                                   '--name',
                                                   'test-deployment',
                                                   '--namespace',
                                                   'anamespace',
                                                   '--local'])
        if result.exception:
            print(''.join(traceback.format_exception(*result.exc_info)))
            self.fail()

        # Branch should be None and local True if using the local state
        mock_head_of.assert_called_once_with(os.getcwd(),
                                             None,
                                             local=True)
        assert mock_docker_image.call_count == 2
        mock_docker_image.assert_has_calls([
            mock.call('build', 'myown.private.registry/test-service:githash'),
            mock.call('push', 'myown.private.registry/test-service:githash')])
        mock_Kube.assert_called_once_with(
            namespace='anamespace',
            deployment_name='test-service',
            printer=kubedeploy.prompt,
            error_printer=kubedeploy.error_prompt)
        kube = mock_Kube.return_value
        kube.apply.assert_called_once_with(
            'myown.private.registry/test-service:githash'
        )


    @mock.patch('twyla.kubedeploy.docker_helpers.docker_image_exists')
    @mock.patch('twyla.kubedeploy.Kube')
    @mock.patch('twyla.kubedeploy.head_of')
    def test_abort_on_dry_run(self,
                              mock_head_of,
                              mock_Kube,
                              mock_docker_exists):
        """
        On dry runs no deployment should be done.
        """
        mock_head_of.return_value = 'githash'
        mock_docker_exists.return_value = True
        runner = CliRunner()
        result = runner.invoke(kubedeploy.deploy, ['--registry',
                                                   'myown.private.registry',
                                                   '--image',
                                                   'test-service',
                                                   '--name',
                                                   'test-deployment',
                                                   '--namespace',
                                                   'anamespace',
                                                   '--dry'])
        if result.exception:
            print(''.join(traceback.format_exception(*result.exc_info)))
            self.fail()
        kube = mock_Kube.return_value
        assert kube.apply.call_count == 0


    @mock.patch('twyla.kubedeploy.error_prompt')
    @mock.patch('twyla.kubedeploy.docker_helpers.docker_image_exists')
    @mock.patch('twyla.kubedeploy.Kube')
    @mock.patch('twyla.kubedeploy.head_of')
    def test_abort_on_missing_image(self, mock_head_of, mock_Kube,
                                    mock_docker_exists, mock_error_prompt):
        """
        If the image does not exist in the registry then no deployment should
        be done.
        """
        mock_head_of.return_value = 'githash'
        mock_docker_exists.return_value = False
        runner = CliRunner()
        runner.invoke(kubedeploy.deploy, ['--registry',
                                          'myown.private.registry',
                                          '--image',
                                          'test-service',
                                          '--name',
                                          'test-deployment',
                                          '--namespace',
                                          'anamespace'])
        # Not checking for the exception on result.exception here,
        # because SystemExit is validly raised for sys.exit(1) on
        # missing image
        kube = mock_Kube.return_value
        assert kube.apply.call_count == 0
        assert mock_error_prompt.call_count == 1
        mock_error_prompt.assert_called_once_with(
            "Image not found: myown.private.registry/test-service:githash")


    @mock.patch('twyla.kubedeploy.docker_helpers.open',
                new=mock.mock_open(read_data=REQUIREMENTS))
    @mock.patch('twyla.kubedeploy.pip')
    @mock.patch('twyla.kubedeploy.os')
    @mock.patch('twyla.kubedeploy.prompt')
    @mock.patch('twyla.kubedeploy.tempfile')
    @mock.patch('twyla.kubedeploy.shutil')
    def test_download_requirements_none(self,
                                        mock_shutil,
                                        mock_tempfile,
                                        mock_prompt,
                                        mock_os,
                                        mock_pip):
        mock_os.path.isfile.return_value = False

        kubedeploy.download_requirements()

        mock_os.path.join.assert_not_called()


    @mock.patch('twyla.kubedeploy.docker_helpers.open',
                new=mock.mock_open(read_data=REQUIREMENTS))
    @mock.patch('twyla.kubedeploy.pip')
    @mock.patch('twyla.kubedeploy.os')
    @mock.patch('twyla.kubedeploy.prompt')
    @mock.patch('twyla.kubedeploy.tempfile')
    @mock.patch('twyla.kubedeploy.shutil')
    def test_download_requirements_cache_exists(self,
                                                mock_shutil,
                                                mock_tempfile,
                                                mock_prompt,
                                                mock_os,
                                                mock_pip):
        mock_os.path.isfile.return_value = True
        mock_os.path.isdir.return_value = True
        mock_os.path.join.return_value = 'some/joined/path'

        kubedeploy.download_requirements()

        mock_os.path.join.assert_called_once_with(mock.ANY, 'pip-cache')
        mock_os.path.isdir.assert_called_once_with(mock.ANY)
        mock_prompt.assert_called_once_with(
            'pip-cache exists. Skipping download of requirements.')
        mock_tempfile.mkdtemp.assert_not_called()


    @mock.patch('twyla.kubedeploy.docker_helpers.open',
                new=mock.mock_open(read_data=REQUIREMENTS))
    @mock.patch('twyla.kubedeploy.pip')
    @mock.patch('twyla.kubedeploy.os')
    @mock.patch('twyla.kubedeploy.prompt')
    @mock.patch('twyla.kubedeploy.tempfile')
    @mock.patch('twyla.kubedeploy.shutil')
    def test_download_requirements(self,
                                   mock_shutil,
                                   mock_tempfile,
                                   mock_prompt,
                                   mock_os,
                                   mock_pip):
        mock_os.path.isfile.return_value = True
        mock_os.path.isdir.return_value = False
        mock_os.path.join.return_value = 'some/joined/path'

        kubedeploy.download_requirements()

        mock_tempfile.mkdtemp.assert_called_once_with()
        mock_prompt.assert_called_once_with('Downloading requirements.')
        mock_pip.main.assert_called_once_with(
            ['download', '-q', '--dest', mock_tempfile.mkdtemp.return_value])
        mock_shutil.move.assert_called_once_with(
            mock_tempfile.mkdtemp.return_value,
            'some/joined/path')


    @mock.patch('twyla.kubedeploy.docker_helpers.open',
                new=mock.mock_open(read_data=REQUIREMENTS))
    @mock.patch('twyla.kubedeploy.pip')
    @mock.patch('twyla.kubedeploy.os')
    @mock.patch('twyla.kubedeploy.prompt')
    @mock.patch('twyla.kubedeploy.tempfile')
    @mock.patch('twyla.kubedeploy.shutil')
    def test_download_requirements_force(self,
                                         mock_shutil,
                                         mock_tempfile,
                                         mock_prompt,
                                         mock_os,
                                         mock_pip):
        mock_os.path.isfile.return_value = True
        mock_os.path.isdir.return_value = True
        mock_os.path.join.return_value = 'some/joined/path'

        kubedeploy.download_requirements(force=True)

        mock_os.path.join.assert_called_once_with(mock.ANY, 'pip-cache')
        mock_os.path.isdir.assert_called_once_with(mock.ANY)
        mock_prompt.assert_has_calls([
            mock.call(
                'pip-cache exists. Removing for fresh download of requirements.'),
            mock.call('Downloading requirements.'),
        ])

        mock_pip.main.assert_called_once_with(
            ['download', '-q', '--dest', mock_tempfile.mkdtemp.return_value])
        mock_shutil.move.assert_called_once_with(
            mock_tempfile.mkdtemp.return_value,
            'some/joined/path')


    @mock.patch('twyla.kubedeploy.docker_helpers.docker_image')
    @mock.patch('twyla.kubedeploy.head_of')
    @mock.patch('twyla.kubedeploy.download_requirements')
    def test_build(self, mock_downloader, mock_head_of, mock_docker_image):
        mock_head_of.return_value = 'githash'
        runner = CliRunner()
        result = runner.invoke(kubedeploy.build, ['--registry',
                                                  'myown.private.registry',
                                                  '--image',
                                                  'test-service'])
        if result.exception:
            print(''.join(traceback.format_exception(*result.exc_info)))
            self.fail()

        # If no version is given explicitly assume local when trying to get the
        # version. This makes sense because builds are using the local state
        # anyway.
        mock_head_of.assert_called_once_with(None, local=True)
        mock_downloader.assert_called_once_with()
        mock_docker_image.assert_called_once_with(
            'build', 'myown.private.registry/test-service:githash')


    @mock.patch('twyla.kubedeploy.docker_helpers.docker_image')
    @mock.patch('twyla.kubedeploy.head_of')
    def test_push(self, mock_head_of, mock_docker_image):
        mock_head_of.return_value = 'githash'
        runner = CliRunner()
        result = runner.invoke(kubedeploy.push, ['--registry',
                                                 'myown.private.registry',
                                                 '--image',
                                                 'test-service'])
        if result.exception:
            print(''.join(traceback.format_exception(*result.exc_info)))
            self.fail()

        # If no version is given explicitly assume local when trying to get the
        # version. This makes sense because builds are using the local state
        # anyway.
        mock_head_of.assert_called_once_with(None, local=True)
        mock_docker_image.assert_called_once_with(
            'push', 'myown.private.registry/test-service:githash')


    @mock.patch('twyla.kubedeploy.Kube')
    def test_info(self, mock_Kube):
        runner = CliRunner()
        result = runner.invoke(kubedeploy.info, ['--name',
                                                 'test-service',
                                                 '--namespace',
                                                 'anamespace'])
        if result.exception:
            print(''.join(traceback.format_exception(*result.exc_info)))
            self.fail()

        mock_Kube.assert_called_once_with(
            namespace='anamespace',
            deployment_name='test-service',
            printer=kubedeploy.prompt,
            error_printer=kubedeploy.error_prompt)
        kube = mock_Kube.return_value
        kube.info.assert_called_once_with()


    @mock.patch('twyla.kubedeploy.Kubectl._list_entities')
    @mock.patch('twyla.kubedeploy.prompt')
    def test_cluster_info(self, mock_printer, mock_cluster_info):
        mock_cluster_info.return_value = {
            'items': [{
                'metadata': {
                    'name': 'deployment1'
                },
                'spec': {
                    'template': {
                        'spec': {
                            'containers': [
                                {
                                    'image': 'myreg/myservice1:ver001'
                                },
                                {
                                    'image': 'myreg/mysidecar1:ver002'
                                }
                            ]
                        }
                    }
                }
            },
            {
                'metadata': {
                    'name': 'deployment2'
                },
                'status': {
                    'replicas': 3,
                    'readyReplicas': 3,
                    'updatedReplicas': 3
                },
                'spec': {
                    'template': {
                        'spec': {
                            'containers': [
                                {
                                    'image': 'myreg/myservice2:ver001'
                                },
                                {
                                    'image': 'myreg/mysidecar2:ver002'
                                }
                            ]
                        }
                    }
                }
            }]
        }
        runner = CliRunner()
        result = runner.invoke(kubedeploy.cluster_info,
                               ['--namespace',
                                'a-namespace'])
        if result.exception:
            print(''.join(traceback.format_exception(*result.exc_info)))
            self.fail()

        mock_cluster_info.assert_called_once_with('deployments', selectors={
            'servicegroup': 'twyla'})


    def test_scrub_cluster_info(self):
        cluster_state = {
            "apiVersion": "v1",
            "items": [
                {
                    "apiVersion": "extensions/v1beta1",
                    "kind": "Deployment",
                    "metadata": {
                        "annotations": {
                            "deployment.kubernetes.io/revision": "88",
                            "kubectl.kubernetes.io/last-applied-configuration": "{\"apiVersion\":\"extensions/v1beta1\",\"kind\":\"Deployment\",\"metadata\":{\"annotations\":{},\"name\":\"test-service\",\"namespace\":\"twyla\"},\"spec\":{\"replicas\":1,\"template\":{\"metadata\":{\"labels\":{\"app\":\"test-service\"}},\"spec\":{\"containers\":[{\"env\":[{\"name\":\"TWYLA_CLUSTER_NAME\",\"valueFrom\":{\"configMapKeyRef\":{\"key\":\"cluster-name\",\"name\":\"cluster-vars\"}}}],\"image\":\"twyla.azurecr.io/test-service:dd2d1f43\",\"imagePullPolicy\":\"Always\",\"name\":\"test-service\"}],\"imagePullSecrets\":[{\"name\":\"twyla-registry-login\"}]}}}}\n"
                        },
                        "creationTimestamp": "2017-10-16T14:55:37Z",
                        "generation": 89,
                        "labels": {
                            "app": "test-service",
                            "servicegroup": "twyla"
                        },
                        "name": "test-service",
                        "namespace": "twyla",
                        "resourceVersion": "16669147",
                        "selfLink": "/apis/extensions/v1beta1/namespaces/twyla/deployments/test-service",
                        "uid": "120abf54-b282-11e7-b58f-000d3a2bee3e"
                    },
                    "spec": {
                        "progressDeadlineSeconds": 600,
                        "replicas": 2,
                        "revisionHistoryLimit": 2,
                        "selector": {
                            "matchLabels": {
                                "app": "test-service"
                            }
                        },
                        "strategy": {
                            "rollingUpdate": {
                                "maxSurge": "50%",
                                "maxUnavailable": "50%"
                            },
                            "type": "RollingUpdate"
                        },
                        "template": {
                            "metadata": {
                                "creationTimestamp": None,
                                "labels": {
                                    "app": "test-service",
                                    "name": "test-service"
                                }
                            },
                            "spec": {
                                "containers": [
                                    {
                                        "env": [
                                            {
                                                "name": "TWYLA_CLUSTER_NAME",
                                                "valueFrom": {
                                                    "configMapKeyRef": {
                                                        "key": "cluster-name",
                                                        "name": "cluster-vars"
                                                    }
                                                }
                                            },
                                            {
                                                "name": "TWYLA_DOCUMENT_STORE_URI",
                                                "valueFrom": {
                                                    "secretKeyRef": {
                                                        "key": "twyla_document_store_string",
                                                        "name": "document-store-secrets"
                                                    }
                                                }
                                            }
                                        ],
                                        "image": "twyla.azurecr.io/test-service:6c66871a",
                                        "imagePullPolicy": "Always",
                                        "name": "test-service",
                                        "resources": {},
                                        "terminationMessagePath": "/dev/termination-log",
                                        "terminationMessagePolicy": "File"
                                    }
                                ],
                                "dnsPolicy": "ClusterFirst",
                                "imagePullSecrets": [
                                    {
                                        "name": "twyla-registry-login"
                            }
                                ],
                                "restartPolicy": "Always",
                                "schedulerName": "default-scheduler",
                                "securityContext": {},
                                "terminationGracePeriodSeconds": 30
                            }
                        }
                    },
                    "status": {
                        "availableReplicas": 2,
                        "conditions": [
                            {
                                "lastTransitionTime": "2018-01-23T08:42:18Z",
                                "lastUpdateTime": "2018-01-23T08:42:18Z",
                                "message": "Deployment has minimum availability.",
                                "reason": "MinimumReplicasAvailable",
                                "status": "True",
                                "type": "Available"
                            },
                            {
                                "lastTransitionTime": "2018-01-08T16:38:21Z",
                                "lastUpdateTime": "2018-02-07T08:27:57Z",
                                "message": "ReplicaSet \"test-service-2416043431\" has successfully progressed.",
                                "reason": "NewReplicaSetAvailable",
                                "status": "True",
                                "type": "Progressing"
                            }
                        ],
                        "observedGeneration": 89,
                        "readyReplicas": 2,
                        "replicas": 2,
                        "updatedReplicas": 2
                    }
                }
            ],
            "kind": "List",
            "metadata": {
                "resourceVersion": "",
                "selfLink": ""
            }
        }
        res = kubedeploy.scrub_cluster_info(cluster_state)

        for item in res:
            assert item.get('status') is None
            assert item['metadata'].get('annotations') is None
            assert item['metadata'].get('creationTimestamp') is None
            assert item['metadata'].get('generation') is None
            assert item['metadata'].get('resourceVersion') is None
            assert item['metadata'].get('selfLink') is None
            assert item['metadata'].get('uid') is None


    @mock.patch('twyla.kubedeploy.Kubectl._list_entities')
    @mock.patch('twyla.kubedeploy.prompt')
    def test_scrub_cluster_info(self, mock_printer, mock_list):
        mock_list.return_value = {
            "apiVersion": "v1",
            "items": [
                {
                    "apiVersion": "extensions/v1beta1",
                    "kind": "Deployment",
                    "metadata": {
                        "annotations": {
                            "deployment.kubernetes.io/revision": "88",
                            "kubectl.kubernetes.io/last-applied-configuration": "{\"apiVersion\":\"extensions/v1beta1\",\"kind\":\"Deployment\",\"metadata\":{\"annotations\":{},\"name\":\"test-service\",\"namespace\":\"twyla\"},\"spec\":{\"replicas\":1,\"template\":{\"metadata\":{\"labels\":{\"app\":\"test-service\"}},\"spec\":{\"containers\":[{\"env\":[{\"name\":\"TWYLA_CLUSTER_NAME\",\"valueFrom\":{\"configMapKeyRef\":{\"key\":\"cluster-name\",\"name\":\"cluster-vars\"}}}],\"image\":\"twyla.azurecr.io/test-service:dd2d1f43\",\"imagePullPolicy\":\"Always\",\"name\":\"test-service\"}],\"imagePullSecrets\":[{\"name\":\"twyla-registry-login\"}]}}}}\n"
                        },
                        "creationTimestamp": "2017-10-16T14:55:37Z",
                        "generation": 89,
                        "labels": {
                            "app": "test-service",
                            "servicegroup": "twyla"
                        },
                        "name": "test-service",
                        "namespace": "twyla",
                        "resourceVersion": "16669147",
                        "selfLink": "/apis/extensions/v1beta1/namespaces/twyla/deployments/test-service",
                        "uid": "120abf54-b282-11e7-b58f-000d3a2bee3e"
                    },
                    "spec": {
                        "progressDeadlineSeconds": 600,
                        "replicas": 2,
                        "revisionHistoryLimit": 2,
                        "selector": {
                            "matchLabels": {
                                "app": "test-service"
                            }
                        },
                        "strategy": {
                            "rollingUpdate": {
                                "maxSurge": "50%",
                                "maxUnavailable": "50%"
                            },
                            "type": "RollingUpdate"
                        },
                        "template": {
                            "metadata": {
                                "creationTimestamp": None,
                                "labels": {
                                    "app": "test-service",
                                    "name": "test-service"
                                }
                            },
                            "spec": {
                                "containers": [
                                    {
                                        "env": [
                                            {
                                                "name": "TWYLA_CLUSTER_NAME",
                                                "valueFrom": {
                                                    "configMapKeyRef": {
                                                        "key": "cluster-name",
                                                        "name": "cluster-vars"
                                                    }
                                                }
                                            },
                                            {
                                                "name": "TWYLA_DOCUMENT_STORE_URI",
                                                "valueFrom": {
                                                    "secretKeyRef": {
                                                        "key": "twyla_document_store_string",
                                                        "name": "document-store-secrets"
                                                    }
                                                }
                                            }
                                        ],
                                        "image": "twyla.azurecr.io/test-service:6c66871a",
                                        "imagePullPolicy": "Always",
                                        "name": "test-service",
                                        "resources": {},
                                        "terminationMessagePath": "/dev/termination-log",
                                        "terminationMessagePolicy": "File"
                                    }
                                ],
                                "dnsPolicy": "ClusterFirst",
                                "imagePullSecrets": [
                                    {
                                        "name": "twyla-registry-login"
                            }
                                ],
                                "restartPolicy": "Always",
                                "schedulerName": "default-scheduler",
                                "securityContext": {},
                                "terminationGracePeriodSeconds": 30
                            }
                        }
                    },
                    "status": {
                        "availableReplicas": 2,
                        "conditions": [
                            {
                                "lastTransitionTime": "2018-01-23T08:42:18Z",
                                "lastUpdateTime": "2018-01-23T08:42:18Z",
                                "message": "Deployment has minimum availability.",
                                "reason": "MinimumReplicasAvailable",
                                "status": "True",
                                "type": "Available"
                            },
                            {
                                "lastTransitionTime": "2018-01-08T16:38:21Z",
                                "lastUpdateTime": "2018-02-07T08:27:57Z",
                                "message": "ReplicaSet \"test-service-2416043431\" has successfully progressed.",
                                "reason": "NewReplicaSetAvailable",
                                "status": "True",
                                "type": "Progressing"
                            }
                        ],
                        "observedGeneration": 89,
                        "readyReplicas": 2,
                        "replicas": 2,
                        "updatedReplicas": 2
                    }
                }
            ],
            "kind": "List",
            "metadata": {
                "resourceVersion": "",
                "selfLink": ""
            }
        }

        tmp = tempfile.NamedTemporaryFile(delete=False)
        runner = CliRunner()
        result = runner.invoke(kubedeploy.cluster_info,
                               ['--namespace',
                                'a-namespace',
                                '--dump-to',
                                tmp.name])
        if result.exception:
            print(''.join(traceback.format_exception(*result.exc_info)))
            self.fail()

        mock_list.assert_called_once_with('deployments', selectors={
            'servicegroup': 'twyla'})

        with open(tmp.name) as fd:
            content = fd.read()

        assert content == '''apiVersion: v1
items:
- apiVersion: extensions/v1beta1
  kind: Deployment
  metadata:
    labels:
      app: test-service
      servicegroup: twyla
    name: test-service
    namespace: twyla
  spec:
    progressDeadlineSeconds: 600
    replicas: 2
    revisionHistoryLimit: 2
    selector:
      matchLabels:
        app: test-service
    strategy:
      rollingUpdate:
        maxSurge: 50%
        maxUnavailable: 50%
      type: RollingUpdate
    template:
      metadata:
        creationTimestamp: null
        labels:
          app: test-service
          name: test-service
      spec:
        containers:
        - env:
          - name: TWYLA_CLUSTER_NAME
            valueFrom:
              configMapKeyRef:
                key: cluster-name
                name: cluster-vars
          - name: TWYLA_DOCUMENT_STORE_URI
            valueFrom:
              secretKeyRef:
                key: twyla_document_store_string
                name: document-store-secrets
          image: twyla.azurecr.io/test-service:6c66871a
          imagePullPolicy: Always
          name: test-service
          resources: {}
          terminationMessagePath: /dev/termination-log
          terminationMessagePolicy: File
        dnsPolicy: ClusterFirst
        imagePullSecrets:
        - name: twyla-registry-login
        restartPolicy: Always
        schedulerName: default-scheduler
        securityContext: {}
        terminationGracePeriodSeconds: 30
kind: List
metadata: {}
'''
