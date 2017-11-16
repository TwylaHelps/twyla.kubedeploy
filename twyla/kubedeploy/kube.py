from typing import Callable

import kubernetes

class KubeException(Exception):
    pass

class Kube:
    def __init__(self,
                 namespace: str,
                 deployment_name: str,
                 printer: Callable[[str], int],
                 error_printer: Callable[[str], int]):
        # Initialize Kubernetes config from ~/.kube/config. Thus this assumes
        # you already have a working kubectl setup.
        kubernetes.config.load_kube_config()
        self.namespace = namespace
        self.v1_client = kubernetes.client.CoreV1Api()
        self.ext_v1_beta_client = kubernetes.client.ExtensionsV1beta1Api()
        self.printer = printer
        self.error_printer = error_printer
        self.deployment_name = deployment_name


    def get_deployment(self):
        is_new = False
        try:
            res = self.ext_v1_beta_client.read_namespaced_deployment(
                name=self.deployment_name,
                namespace=self.namespace)
            return res, is_new
        except kubernetes.client.rest.ApiException as e:
            # Create a new deployment if no existing is found
            if e.status == 404:
                msg = "No deployment found for {}".format(self.deployment_name)
                raise KubeException(msg) from None
            else:
                raise e


    def deploy(self, tag: str):
        # Get current deployment and update the relevant information
        deployment, is_new = self.get_deployment()
        deployment = self.fill_deployment_definition(deployment, tag)

        api_client = kubernetes.client.ExtensionsV1beta1Api()
        try:
            if is_new:
                api_client.create_namespaced_deployment(
                    body=deployment,
                    namespace=self.namespace)
            else:
                api_client.patch_namespaced_deployment(
                    name=deployment.metadata.name,
                    body=deployment,
                    namespace=self.namespace)

            self.printer("Deployment successful. It may need some time to "
                         "propagate.")
        except kubernetes.client.rest.ApiException as e:
            self.error_printer(e)

    @property
    def current_context(self):
        return kubernetes.config.list_kube_config_contexts()[1]['name']


    def info(self):
        kubernetes.config.load_kube_config()
        deployment, _ = self.get_deployment()
        self.print_deployment_info('Current {}'.format(self.deployment_name),
                                   deployment)

    def print_deployment_info(
            self,
            title: str,
            deployment: kubernetes.client.ExtensionsV1beta1Deployment):

        if deployment.spec is None:
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
            deployment: kubernetes.client.ExtensionsV1beta1Deployment,
            tag: str):
        # Set name
        deployment.metadata.name = self.deployment_name
        deployment.spec.template.metadata.labels['name'] = self.deployment_name
        deployment.spec.revisionHistoryLimit = 5

        # Set image. For now just grab the first container as there is only one
        # TODO: find a way to properly decide on the container to update here
        deployment.spec.template.spec.containers[0].image = tag

        return deployment
