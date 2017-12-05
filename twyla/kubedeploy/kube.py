import json
from typing import Callable

import kubernetes
import yaml


class DeploymentNotFoundException(Exception):
    pass


class MultipleDeploymentDefinitionsException(Exception):
    pass


class ServiceNotFoundException(Exception):
    pass


class MultipleServicesDefinitionsException(Exception):
    pass


# Be like Response, my friend!
# Implements res.data to make the Kubernetes deserializer work with dicts.
class Res:
    def __init__(self, data):
        self.data = data


class KubeObjects(list):
    def get_deployment(self):
        deployment_data = [obj for obj
                           in self
                           if obj is not None
                           and obj.kind == 'Deployment']
        if len(deployment_data) > 1:
            raise MultipleDeploymentDefinitionsException
        elif len(deployment_data) < 1:
            raise DeploymentNotFoundException

        return deployment_data[0]

    # TODO: make dry
    def get_service(self):
        deployment_data = [obj for obj
                           in self
                           if obj is not None
                           and obj.kind == 'Service']
        if len(deployment_data) > 1:
            raise MultipleServicesDefinitionsException
        elif len(deployment_data) < 1:
            raise ServiceNotFoundException

        return deployment_data[0]


class Kube:
    def __init__(self,
                 namespace: str,
                 deployment_name: str,
                 printer: Callable[[str], int],
                 error_printer: Callable[[str], int],
                 deployment_template: str=None):
        # Initialize Kubernetes config from ~/.kube/config. Thus this assumes
        # you already have a working kubectl setup.
        kubernetes.config.load_kube_config()
        self.namespace = namespace
        self.v1_client = kubernetes.client.CoreV1Api()
        self.ext_v1_beta_client = kubernetes.client.AppsV1beta1Api()
        self.printer = printer
        self.error_printer = error_printer
        self.deployment_name = deployment_name
        self.deployment_template = deployment_template or 'deployment.yml'
        self.objects = KubeObjects()


    def type_name_from_data(self, data):
        # apps/v1beta1
        api_version = data.get('apiVersion')
        # Deployment
        kind = data.get('kind')
        # ['Apps', 'V1beta1']
        parts = [part.capitalize() for part in api_version.split('/')]
        # ['Apps', 'V1beta1', 'Deployment']
        parts.append(kind)
        # 'AppsV1beta1Deployment'
        return ''.join(parts)


    def parse_data(self, data: dict):
        kubernetes_type = self.type_name_from_data(data)
        api_client = kubernetes.client.ApiClient()
        res = Res(data=json.dumps(data))
        return api_client.deserialize(res, kubernetes_type)


    def load_objects_from_file(self):
        with open(self.deployment_template) as fd:
            documents = yaml.load_all(fd)

        objects = [self.parse_data(doc) for doc
                   in documents
                   if doc is not None]

        self.objects.extend(objects)


    def get_remote_deployment(self):
        try:
            res = self.ext_v1_beta_client.read_namespaced_deployment(
                name=self.deployment_name,
                namespace=self.namespace)
            return res
        except kubernetes.client.rest.ApiException as e:
            # Create a new deployment if no existing is found
            if e.status == 404:
                msg = "No deployment found for {}".format(self.deployment_name)
                raise DeploymentNotFoundException(msg) from None
            else:
                raise e


    def get_remote_service(self):
        try:
            res = self.ext_v1_beta_client.read_namespaced_service(
                name=self.deployment_name,
                namespace=self.namespace)
            return res
        except kubernetes.client.rest.ApiException as e:
            # Create a new service if no existing is found
            if e.status == 404:
                msg = "No service found for {}".format(self.deployment_name)
                raise ServiceNotFoundException(msg) from None
            else:
                raise e


    def apply(self, tag: str):
        # Load the deployment definition
        self.load_objects_from_file()
        self.apply_deployment(tag)
        self.apply_service()


    def apply_deployment(self, tag: str):
        # Get current deployment and update the relevant information
        try:
            deployment = self.fill_deployment_definition(
                self.objects.get_deployment(), tag)
        except MultipleDeploymentDefinitionsException as multi:
            self.error_printer(
                'Only one deployment is currently allowed in deployment.yml')
            return
        except DeploymentNotFoundException as not_found:
            self.error_printer(
                'No deployment definition found in deployment.yml')
            return

        api_client = kubernetes.client.AppsV1beta1Api()
        try:
            # The call to get the deployment is basically a sentinel to decide
            # if the deployment definition has to be supplied with patch or
            # create.
            self.get_remote_deployment()
            api_client.patch_namespaced_deployment(
                name=deployment.metadata.name,
                body=deployment,
                namespace=self.namespace)
            self.printer("Deployment successfully updated.")
            self.printer("It may need some time to propagate.")
        except DeploymentNotFoundException as not_found:
            api_client.create_namespaced_deployment(
                body=deployment,
                namespace=self.namespace)
            self.printer("New deployment successfully created")
            self.printer("It may need some time to propagate.")
        except kubernetes.client.rest.ApiException as e:
            self.error_printer(e)


    def apply_service(self):
        # Get current deployment and update the relevant information
        try:
            service = self.fill_service_definition(self.objects.get_service())
        except MultipleServicesDefinitionsException as multi:
            self.error_printer(
                'Only one service is currently allowed in deployment.yml')
            return
        except ServiceNotFoundException as not_found:
            self.printer(
                'No service definition found in deployment.yml. Skipping')
            return

        api_client = kubernetes.client.AppsV1beta1Api()
        try:
            # The call to get the service is basically a sentinel to decide
            # if the deployment definition has to be supplied with patch or
            # create.
            self.get_remote_service()
            api_client.patch_namespaced_service(
                name=service.metadata.name,
                body=service,
                namespace=self.namespace)
            self.printer("Service successfully updated.")
        except ServiceNotFoundException as not_found:
            api_client.create_namespaced_service(
                body=service,
                namespace=self.namespace)
            self.printer("New service successfully created")
        except kubernetes.client.rest.ApiException as e:
            self.error_printer(e)


    def info(self):
        kubernetes.config.load_kube_config()
        try:
            deployment = self.get_remote_deployment()
            self.print_deployment_info(
                'Current {}'.format(self.deployment_name),
                deployment)
        except DeploymentNotFoundException as not_found:
            self.error_printer(not_found)


    def print_deployment_info(
            self,
            title: str,
            deployment: kubernetes.client.AppsV1beta1Deployment):

        if deployment.spec is None:
            # NOTE: This code path can not be hit I think?
            self.printer("??? is not deployed.")
        else:
            self.printer("{}:".format(title))
            for c in deployment.spec.template.spec.containers:
                self.printer('image: {}'.format(c.image), 4)

                # If no deployment exists in the slot, status will be None
                if deployment.status is None:
                    self.printer('replicas: no deployment', 4)
                else:
                    self.printer('replicas: {}/{}'.format(
                        deployment.status.ready_replicas,
                        deployment.status.replicas), 4)


    def fill_deployment_definition(
            self,
            deployment: kubernetes.client.AppsV1beta1Deployment,
            tag: str):
        # Set name
        deployment.metadata.name = self.deployment_name
        deployment.spec.template.metadata.labels['name'] = self.deployment_name
        deployment.spec.revisionHistoryLimit = 5

        # Set image. For now just grab the first container as there is only one
        # TODO: find a way to properly decide on the container to update here
        deployment.spec.template.spec.containers[0].image = tag

        return deployment


    def fill_service_definition(
            self,
            service: kubernetes.client.V1Service):
        # Set name
        service.metadata.name = self.deployment_name
        service.spec.selector['app'] = self.deployment_name

        return service
