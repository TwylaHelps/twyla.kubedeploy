import json
import pytest
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

        assert error.value.args[0].endswith(b'No such file or directory\n')

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

        mock_call.assert_called_once_with(expected_call)


    @mock.patch('twyla.kubedeploy.kubectl.Kubectl._call')
    def test_list_deployments(self, mock_call):
        expected = ['get', 'deployments', '-o', 'json']
        expected_call = ['kubectl', '--namespace', 'test-space']
        expected_call.extend(expected)
        kubectl = Kubectl()
        kubectl.namespace = 'test-space'
        kubectl.list_deployments()

        mock_call.assert_called_once_with(expected_call)


    @mock.patch('twyla.kubedeploy.kubectl.Kubectl._call')
    def test_list_deployments_sorted(self, mock_call):
        expected = ['get', 'deployments', '-o', 'json',
                    '--sort-by', 'something']
        expected_call = ['kubectl', '--namespace', 'test-space']
        expected_call.extend(expected)
        kubectl = Kubectl()
        kubectl.namespace = 'test-space'
        kubectl.list_deployments(sort_by='something')

        mock_call.assert_called_once_with(expected_call)


    @mock.patch('twyla.kubedeploy.kubectl.Kubectl._call')
    def test_list_deployments_by_selector(self, mock_call):
        expected = ['get', 'deployments', '--selector',
                    'servicegroup=twyla,mylabel=myvalue', '-o', 'json']
        expected_call = ['kubectl', '--namespace', 'test-space']
        expected_call.extend(expected)
        kubectl = Kubectl()
        kubectl.namespace = 'test-space'
        kubectl.list_deployments(selectors={'servicegroup': 'twyla',
                                            'mylabel': 'myvalue'})

        mock_call.assert_called_once_with(expected_call)


    def test_make_selector_args(self):
        kubectl = Kubectl()
        res = kubectl._make_selector_args(None)
        assert res == []
        res = kubectl._make_selector_args({})
        assert res == []
        res = kubectl._make_selector_args({'one': 'val'})
        assert res == ['--selector', 'one=val']
        res = kubectl._make_selector_args({'one': 'val', 'two': 'val2'})
        assert res == ['--selector', 'one=val,two=val2']


    @mock.patch('twyla.kubedeploy.kubectl.Kubectl._call')
    def test_update_replicas(self, mock_call):
        kube_list = json.loads('''
{
    "apiVersion": "v1",
    "items": [
        {
            "apiVersion": "extensions/v1beta1",
            "kind": "Deployment",
            "metadata": {
                "labels": {
                    "app": "test-service-one",
                    "servicegroup": "twyla"
                },
                "name": "test-service-one",
                "namespace": "twyla"
            },
            "spec": {
                "replicas": 2,
                "selector": {
                    "matchLabels": {
                        "app": "test-service-one",
                        "name": "test-service-one"
                    }
                },
                "strategy": {
                    "rollingUpdate": {
                        "maxSurge": "0%",
                        "maxUnavailable": "100%"
                    },
                    "type": "RollingUpdate"
                },
                "template": {
                    "metadata": {
                        "creationTimestamp": null,
                        "labels": {
                            "app": "test-service-one",
                            "name": "test-service-one"
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
                                    }
                                ],
                                "image": "twyla.azurecr.io/test-service-one:cc0cd960",
                                "imagePullPolicy": "Always",
                                "name": "test-service-one",
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
            }
        },
        {
            "apiVersion": "extensions/v1beta1",
            "kind": "Deployment",
            "metadata": {
                "labels": {
                    "app": "test-service-two",
                    "servicegroup": "twyla"
                },
                "name": "test-service-two",
                "namespace": "twyla"
            },
            "spec": {
                "progressDeadlineSeconds": 600,
                "replicas": 1,
                "revisionHistoryLimit": 2,
                "selector": {
                    "matchLabels": {
                        "app": "test-service-two"
                    }
                },
                "strategy": {
                    "rollingUpdate": {
                        "maxSurge": 1,
                        "maxUnavailable": 1
                    },
                    "type": "RollingUpdate"
                },
                "template": {
                    "metadata": {
                        "creationTimestamp": null,
                        "labels": {
                            "app": "test-service-two",
                            "name": "test-service-two"
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
                                    }
                                ],
                                "image": "twyla.azurecr.io/test-service-two:c42d0ebe",
                                "imagePullPolicy": "Always",
                                "name": "test-service-two",
                                "ports": [
                                    {
                                        "containerPort": 5000,
                                        "protocol": "TCP"
                                    }
                                ],
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
            }
        }
    ],
    "kind": "List",
    "metadata": {
        "resourceVersion": "",
        "selfLink": ""
    }
}
        ''')
        dep1 = json.loads('''{
   "apiVersion":"extensions/v1beta1",
   "kind":"Deployment",
   "metadata":{
      "annotations":{
         "deployment.kubernetes.io/revision":"89",
         "kubectl.kubernetes.io/last-applied-configuration":"{\\"apiVersion\\":\\"extensions/v1beta1\\",\\"kind\\":\\"Deployment\\",\\"metadata\\":{\\"annotations\\":{},\\"labels\\":{\\"app\\":\\"test-service-one\\",\\"servicegroup\\":\\"twyla\\"},\\"name\\":\\"test-service-one\\",\\"namespace\\":\\"twyla\\"},\\"spec\\":{\\"progressDeadlineSeconds\\":600,\\"replicas\\":1,\\"revisionHistoryLimit\\":2,\\"selector\\":{\\"matchLabels\\":{\\"app\\":\\"test-service-one\\"}},\\"strategy\\":{\\"rollingUpdate\\":{\\"maxSurge\\":\\"50%\\",\\"maxUnavailable\\":\\"50%\\"},\\"type\\":\\"RollingUpdate\\"},\\"template\\":{\\"metadata\\":{\\"creationTimestamp\\":null,\\"labels\\":{\\"app\\":\\"test-service-one\\",\\"name\\":\\"test-service-one\\"}},\\"spec\\":{\\"containers\\":[{\\"env\\":[{\\"name\\":\\"TWYLA_CLUSTER_NAME\\",\\"valueFrom\\":{\\"configMapKeyRef\\":{\\"key\\":\\"cluster-name\\",\\"name\\":\\"cluster-vars\\"}}},{\\"name\\":\\"TWYLA_DOCUMENT_STORE_URI\\",\\"valueFrom\\":{\\"secretKeyRef\\":{\\"key\\":\\"twyla_document_store_string\\",\\"name\\":\\"document-store-secrets\\"}}}],\\"image\\":\\"twyla.azurecr.io/test-service-one:356dcef4\\",\\"imagePullPolicy\\":\\"Always\\",\\"name\\":\\"test-service-one\\",\\"resources\\":{},\\"terminationMessagePath\\":\\"/dev/termination-log\\",\\"terminationMessagePolicy\\":\\"File\\"}],\\"dnsPolicy\\":\\"ClusterFirst\\",\\"imagePullSecrets\\":[{\\"name\\":\\"twyla-registry-login\\"}],\\"restartPolicy\\":\\"Always\\",\\"schedulerName\\":\\"default-scheduler\\",\\"securityContext\\":{},\\"terminationGracePeriodSeconds\\":30}}}}\\n"
      },
      "creationTimestamp":"2017-10-16T14:55:37Z",
      "generation":95,
      "labels":{
         "app":"test-service-one",
         "servicegroup":"twyla"
      },
      "name":"test-service-one",
      "namespace":"twyla",
      "resourceVersion":"16810663",
      "selfLink":"/apis/extensions/v1beta1/namespaces/twyla/deployments/test-service-one",
      "uid":"120abf54-b282-11e7-b58f-000d3a2bee3e"
   },
   "spec":{
      "progressDeadlineSeconds":600,
      "replicas":1,
      "revisionHistoryLimit":2,
      "selector":{
         "matchLabels":{
            "app":"test-service-one"
         }
      },
      "strategy":{
         "rollingUpdate":{
            "maxSurge":"50%",
            "maxUnavailable":"50%"
         },
         "type":"RollingUpdate"
      },
      "template":{
         "metadata":{
            "creationTimestamp":null,
            "labels":{
               "app":"test-service-one",
               "name":"test-service-one"
            }
         },
         "spec":{
            "containers":[
               {
                  "env":[
                     {
                        "name":"TWYLA_CLUSTER_NAME",
                        "valueFrom":{
                           "configMapKeyRef":{
                              "key":"cluster-name",
                              "name":"cluster-vars"
                           }
                        }
                     },
                     {
                        "name":"TWYLA_DOCUMENT_STORE_URI",
                        "valueFrom":{
                           "secretKeyRef":{
                              "key":"twyla_document_store_string",
                              "name":"document-store-secrets"
                           }
                        }
                     }
                  ],
                  "image":"twyla.azurecr.io/test-service-one:356dcef4",
                  "imagePullPolicy":"Always",
                  "name":"test-service-one",
                  "resources":{

                  },
                  "terminationMessagePath":"/dev/termination-log",
                  "terminationMessagePolicy":"File"
               }
            ],
            "dnsPolicy":"ClusterFirst",
            "imagePullSecrets":[
               {
                  "name":"twyla-registry-login"
               }
            ],
            "restartPolicy":"Always",
            "schedulerName":"default-scheduler",
            "securityContext":{

            },
            "terminationGracePeriodSeconds":30
         }
      }
   },
   "status":{
      "availableReplicas":1,
      "conditions":[
         {
            "lastTransitionTime":"2018-01-08T16:38:21Z",
            "lastUpdateTime":"2018-02-13T18:47:02Z",
            "message":"ReplicaSet \\"test-service-one-3114667387\\" has successfully progressed.",
            "reason":"NewReplicaSetAvailable",
            "status":"True",
            "type":"Progressing"
         },
         {
            "lastTransitionTime":"2018-02-14T16:36:34Z",
            "lastUpdateTime":"2018-02-14T16:36:34Z",
            "message":"Deployment has minimum availability.",
            "reason":"MinimumReplicasAvailable",
            "status":"True",
            "type":"Available"
         }
      ],
      "observedGeneration":95,
      "readyReplicas":1,
      "replicas":1,
      "updatedReplicas":1
   }
}''')
        dep2 = json.loads('''{
   "apiVersion":"extensions/v1beta1",
   "kind":"Deployment",
   "metadata":{
      "annotations":{
         "deployment.kubernetes.io/revision":"89",
         "kubectl.kubernetes.io/last-applied-configuration":"{\\"apiVersion\\":\\"extensions/v1beta1\\",\\"kind\\":\\"Deployment\\",\\"metadata\\":{\\"annotations\\":{},\\"labels\\":{\\"app\\":\\"test-service-two\\",\\"servicegroup\\":\\"twyla\\"},\\"name\\":\\"xpi\\",\\"namespace\\":\\"twyla\\"},\\"spec\\":{\\"progressDeadlineSeconds\\":600,\\"replicas\\":1,\\"revisionHistoryLimit\\":2,\\"selector\\":{\\"matchLabels\\":{\\"app\\":\\"xpi\\"}},\\"strategy\\":{\\"rollingUpdate\\":{\\"maxSurge\\":\\"50%\\",\\"maxUnavailable\\":\\"50%\\"},\\"type\\":\\"RollingUpdate\\"},\\"template\\":{\\"metadata\\":{\\"creationTimestamp\\":null,\\"labels\\":{\\"app\\":\\"xpi\\",\\"name\\":\\"xpi\\"}},\\"spec\\":{\\"containers\\":[{\\"env\\":[{\\"name\\":\\"TWYLA_CLUSTER_NAME\\",\\"valueFrom\\":{\\"configMapKeyRef\\":{\\"key\\":\\"cluster-name\\",\\"name\\":\\"cluster-vars\\"}}},{\\"name\\":\\"TWYLA_DOCUMENT_STORE_URI\\",\\"valueFrom\\":{\\"secretKeyRef\\":{\\"key\\":\\"twyla_document_store_string\\",\\"name\\":\\"document-store-secrets\\"}}}],\\"image\\":\\"twyla.azurecr.io/xpi:356dcef4\\",\\"imagePullPolicy\\":\\"Always\\",\\"name\\":\\"xpi\\",\\"resources\\":{},\\"terminationMessagePath\\":\\"/dev/termination-log\\",\\"terminationMessagePolicy\\":\\"File\\"}],\\"dnsPolicy\\":\\"ClusterFirst\\",\\"imagePullSecrets\\":[{\\"name\\":\\"twyla-registry-login\\"}],\\"restartPolicy\\":\\"Always\\",\\"schedulerName\\":\\"default-scheduler\\",\\"securityContext\\":{},\\"terminationGracePeriodSeconds\\":30}}}}\\n"
      },
      "creationTimestamp":"2017-10-16T14:55:37Z",
      "generation":95,
      "labels":{
         "app":"test-service-two",
         "servicegroup":"twyla"
      },
      "name":"test-service-two",
      "namespace":"twyla",
      "resourceVersion":"16810663",
      "selfLink":"/apis/extensions/v1beta1/namespaces/twyla/deployments/test-service-two",
      "uid":"120abf54-b282-11e7-b58f-000d3a2bee3e"
   },
   "spec":{
      "progressDeadlineSeconds":600,
      "replicas":3,
      "revisionHistoryLimit":2,
      "selector":{
         "matchLabels":{
            "app":"test-service-two"
         }
      },
      "strategy":{
         "rollingUpdate":{
            "maxSurge":"50%",
            "maxUnavailable":"50%"
         },
         "type":"RollingUpdate"
      },
      "template":{
         "metadata":{
            "creationTimestamp":null,
            "labels":{
               "app":"test-service-two",
               "name":"test-service-two"
            }
         },
         "spec":{
            "containers":[
               {
                  "env":[
                     {
                        "name":"TWYLA_CLUSTER_NAME",
                        "valueFrom":{
                           "configMapKeyRef":{
                              "key":"cluster-name",
                              "name":"cluster-vars"
                           }
                        }
                     },
                     {
                        "name":"TWYLA_DOCUMENT_STORE_URI",
                        "valueFrom":{
                           "secretKeyRef":{
                              "key":"twyla_document_store_string",
                              "name":"document-store-secrets"
                           }
                        }
                     }
                  ],
                  "image":"twyla.azurecr.io/test-service-two:356dcef4",
                  "imagePullPolicy":"Always",
                  "name":"test-service-two",
                  "resources":{

                  },
                  "terminationMessagePath":"/dev/termination-log",
                  "terminationMessagePolicy":"File"
               }
            ],
            "dnsPolicy":"ClusterFirst",
            "imagePullSecrets":[
               {
                  "name":"twyla-registry-login"
               }
            ],
            "restartPolicy":"Always",
            "schedulerName":"default-scheduler",
            "securityContext":{

            },
            "terminationGracePeriodSeconds":30
         }
      }
   },
   "status":{
      "availableReplicas":3,
      "conditions":[
         {
            "lastTransitionTime":"2018-01-08T16:38:21Z",
            "lastUpdateTime":"2018-02-13T18:47:02Z",
            "message":"ReplicaSet \\"test-service-two-3114667387\\" has successfully progressed.",
            "reason":"NewReplicaSetAvailable",
            "status":"True",
            "type":"Progressing"
         },
         {
            "lastTransitionTime":"2018-02-14T16:36:34Z",
            "lastUpdateTime":"2018-02-14T16:36:34Z",
            "message":"Deployment has minimum availability.",
            "reason":"MinimumReplicasAvailable",
            "status":"True",
            "type":"Available"
         }
      ],
      "observedGeneration":95,
      "readyReplicas":3,
      "replicas":3,
      "updatedReplicas":3
   }
}''')
        mock_call.side_effect = [
            dep1,
            dep2
        ]

        # before (this makes the test more obvious)
        assert kube_list['items'][0]['spec']['replicas'] == 2
        assert kube_list['items'][1]['spec']['replicas'] == 1

        kubectl = Kubectl()
        kubectl.update_replicas(kube_list)

        # after
        assert kube_list['items'][0]['spec']['replicas'] == 1
        assert kube_list['items'][1]['spec']['replicas'] == 3


    @mock.patch('twyla.kubedeploy.kubectl.Kubectl._call')
    def test_update_replicas_no_remote(self, mock_call):
        kube_list = json.loads('''
{
    "apiVersion": "v1",
    "items": [
        {
            "apiVersion": "extensions/v1beta1",
            "kind": "Deployment",
            "metadata": {
                "labels": {
                    "app": "test-service-one",
                    "servicegroup": "twyla"
                },
                "name": "test-service-one",
                "namespace": "twyla"
            },
            "spec": {
                "replicas": 2,
                "selector": {
                    "matchLabels": {
                        "app": "test-service-one",
                        "name": "test-service-one"
                    }
                },
                "strategy": {
                    "rollingUpdate": {
                        "maxSurge": "0%",
                        "maxUnavailable": "100%"
                    },
                    "type": "RollingUpdate"
                },
                "template": {
                    "metadata": {
                        "creationTimestamp": null,
                        "labels": {
                            "app": "test-service-one",
                            "name": "test-service-one"
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
                                    }
                                ],
                                "image": "twyla.azurecr.io/test-service-one:cc0cd960",
                                "imagePullPolicy": "Always",
                                "name": "test-service-one",
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
            }
        },
        {
            "apiVersion": "extensions/v1beta1",
            "kind": "Deployment",
            "metadata": {
                "labels": {
                    "app": "test-service-two",
                    "servicegroup": "twyla"
                },
                "name": "test-service-two",
                "namespace": "twyla"
            },
            "spec": {
                "progressDeadlineSeconds": 600,
                "replicas": 1,
                "revisionHistoryLimit": 2,
                "selector": {
                    "matchLabels": {
                        "app": "test-service-two"
                    }
                },
                "strategy": {
                    "rollingUpdate": {
                        "maxSurge": 1,
                        "maxUnavailable": 1
                    },
                    "type": "RollingUpdate"
                },
                "template": {
                    "metadata": {
                        "creationTimestamp": null,
                        "labels": {
                            "app": "test-service-two",
                            "name": "test-service-two"
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
                                    }
                                ],
                                "image": "twyla.azurecr.io/test-service-two:c42d0ebe",
                                "imagePullPolicy": "Always",
                                "name": "test-service-two",
                                "ports": [
                                    {
                                        "containerPort": 5000,
                                        "protocol": "TCP"
                                    }
                                ],
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
            }
        }
    ],
    "kind": "List",
    "metadata": {
        "resourceVersion": "",
        "selfLink": ""
    }
}
        ''')
        dep1 = json.loads('''{
   "apiVersion":"extensions/v1beta1",
   "kind":"Deployment",
   "metadata":{
      "annotations":{
         "deployment.kubernetes.io/revision":"89",
         "kubectl.kubernetes.io/last-applied-configuration":"{\\"apiVersion\\":\\"extensions/v1beta1\\",\\"kind\\":\\"Deployment\\",\\"metadata\\":{\\"annotations\\":{},\\"labels\\":{\\"app\\":\\"test-service-one\\",\\"servicegroup\\":\\"twyla\\"},\\"name\\":\\"test-service-one\\",\\"namespace\\":\\"twyla\\"},\\"spec\\":{\\"progressDeadlineSeconds\\":600,\\"replicas\\":1,\\"revisionHistoryLimit\\":2,\\"selector\\":{\\"matchLabels\\":{\\"app\\":\\"test-service-one\\"}},\\"strategy\\":{\\"rollingUpdate\\":{\\"maxSurge\\":\\"50%\\",\\"maxUnavailable\\":\\"50%\\"},\\"type\\":\\"RollingUpdate\\"},\\"template\\":{\\"metadata\\":{\\"creationTimestamp\\":null,\\"labels\\":{\\"app\\":\\"test-service-one\\",\\"name\\":\\"test-service-one\\"}},\\"spec\\":{\\"containers\\":[{\\"env\\":[{\\"name\\":\\"TWYLA_CLUSTER_NAME\\",\\"valueFrom\\":{\\"configMapKeyRef\\":{\\"key\\":\\"cluster-name\\",\\"name\\":\\"cluster-vars\\"}}},{\\"name\\":\\"TWYLA_DOCUMENT_STORE_URI\\",\\"valueFrom\\":{\\"secretKeyRef\\":{\\"key\\":\\"twyla_document_store_string\\",\\"name\\":\\"document-store-secrets\\"}}}],\\"image\\":\\"twyla.azurecr.io/test-service-one:356dcef4\\",\\"imagePullPolicy\\":\\"Always\\",\\"name\\":\\"test-service-one\\",\\"resources\\":{},\\"terminationMessagePath\\":\\"/dev/termination-log\\",\\"terminationMessagePolicy\\":\\"File\\"}],\\"dnsPolicy\\":\\"ClusterFirst\\",\\"imagePullSecrets\\":[{\\"name\\":\\"twyla-registry-login\\"}],\\"restartPolicy\\":\\"Always\\",\\"schedulerName\\":\\"default-scheduler\\",\\"securityContext\\":{},\\"terminationGracePeriodSeconds\\":30}}}}\\n"
      },
      "creationTimestamp":"2017-10-16T14:55:37Z",
      "generation":95,
      "labels":{
         "app":"test-service-one",
         "servicegroup":"twyla"
      },
      "name":"test-service-one",
      "namespace":"twyla",
      "resourceVersion":"16810663",
      "selfLink":"/apis/extensions/v1beta1/namespaces/twyla/deployments/test-service-one",
      "uid":"120abf54-b282-11e7-b58f-000d3a2bee3e"
   },
   "spec":{
      "progressDeadlineSeconds":600,
      "replicas":1,
      "revisionHistoryLimit":2,
      "selector":{
         "matchLabels":{
            "app":"test-service-one"
         }
      },
      "strategy":{
         "rollingUpdate":{
            "maxSurge":"50%",
            "maxUnavailable":"50%"
         },
         "type":"RollingUpdate"
      },
      "template":{
         "metadata":{
            "creationTimestamp":null,
            "labels":{
               "app":"test-service-one",
               "name":"test-service-one"
            }
         },
         "spec":{
            "containers":[
               {
                  "env":[
                     {
                        "name":"TWYLA_CLUSTER_NAME",
                        "valueFrom":{
                           "configMapKeyRef":{
                              "key":"cluster-name",
                              "name":"cluster-vars"
                           }
                        }
                     },
                     {
                        "name":"TWYLA_DOCUMENT_STORE_URI",
                        "valueFrom":{
                           "secretKeyRef":{
                              "key":"twyla_document_store_string",
                              "name":"document-store-secrets"
                           }
                        }
                     }
                  ],
                  "image":"twyla.azurecr.io/test-service-one:356dcef4",
                  "imagePullPolicy":"Always",
                  "name":"test-service-one",
                  "resources":{

                  },
                  "terminationMessagePath":"/dev/termination-log",
                  "terminationMessagePolicy":"File"
               }
            ],
            "dnsPolicy":"ClusterFirst",
            "imagePullSecrets":[
               {
                  "name":"twyla-registry-login"
               }
            ],
            "restartPolicy":"Always",
            "schedulerName":"default-scheduler",
            "securityContext":{

            },
            "terminationGracePeriodSeconds":30
         }
      }
   },
   "status":{
      "availableReplicas":1,
      "conditions":[
         {
            "lastTransitionTime":"2018-01-08T16:38:21Z",
            "lastUpdateTime":"2018-02-13T18:47:02Z",
            "message":"ReplicaSet \\"test-service-one-3114667387\\" has successfully progressed.",
            "reason":"NewReplicaSetAvailable",
            "status":"True",
            "type":"Progressing"
         },
         {
            "lastTransitionTime":"2018-02-14T16:36:34Z",
            "lastUpdateTime":"2018-02-14T16:36:34Z",
            "message":"Deployment has minimum availability.",
            "reason":"MinimumReplicasAvailable",
            "status":"True",
            "type":"Available"
         }
      ],
      "observedGeneration":95,
      "readyReplicas":1,
      "replicas":1,
      "updatedReplicas":1
   }
}''')
        mock_call.side_effect = [
            dep1,
            KubectlCallFailed
        ]

        # before (this makes the test more obvious)
        assert kube_list['items'][0]['spec']['replicas'] == 2
        assert kube_list['items'][1]['spec']['replicas'] == 1

        kubectl = Kubectl()
        kubectl.update_replicas(kube_list)

        # after
        assert kube_list['items'][0]['spec']['replicas'] == 1
        assert kube_list['items'][1]['spec']['replicas'] == 1
