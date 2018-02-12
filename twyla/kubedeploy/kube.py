import tempfile
from typing import Callable

from jinja2 import Environment, Template, FileSystemLoader

from twyla.kubedeploy.kubectl import Kubectl, KubectlCallFailed


class DeploymentNotFoundException(Exception):
    pass


class Kube:
    def __init__(self,
                 namespace: str,
                 deployment_name: str,
                 printer: Callable[[str], int],
                 error_printer: Callable[[str], int],
                 deployment_template: str=None):
        self.printer = printer
        self.error_printer = error_printer
        self.deployment_name = deployment_name
        self.deployment_template = deployment_template or 'deployment.yml'
        self.kubectl = Kubectl()
        self.kubectl.namespace = namespace


    def get_remote_deployment(self):
        return self.kubectl.get_deployment(self.deployment_name)


    def apply(self, tag: str):
        # Load the deployment definition
        file_name = self.render_template(tag)
        output = self.kubectl.apply(file_name)
        for line in output.split('\n'):
            if line is not '':
                self.printer(line)


    def info(self):
        try:
            deployment = self.get_remote_deployment()
            self.print_deployment_info(
                'Current {}'.format(self.deployment_name),
                deployment)
        except KubectlCallFailed as e:
            self.error_printer(self.exception(e))


    def exception(self, e):
        return e.args[0].decode('utf8').strip()


    def print_deployment_info(
            self,
            title: str,
            deployment):

        info_template = Template('''
{%- for c in deployment.spec.template.spec.containers -%}
{{ meta.title }}:
    image: {{ c.image }}
    replicas: {{ deployment.status.readyReplicas }}/{{ deployment.status.replicas }}
{%- endfor -%}
        ''')

        rendered = info_template.render(meta={'name': self.deployment_name,
                                              'title': title},
                                        deployment=deployment)

        for line in rendered.split('\n'):
            self.printer(line)

        return


    def render_template(self, tag: str):
        jinja = Environment(loader=FileSystemLoader('./'))
        template = jinja.get_template(self.deployment_template)

        replicas = None
        try:
            deployment = self.get_remote_deployment()
            replicas = deployment['spec']['replicas']

            # make sure to use the same number of replicas as remote to honor
            # scaling
            if deployment.get('status'):
                replicas = deployment['status']['replicas']
        except KubectlCallFailed as e:
            self.error_printer(self.exception(e))

        data = {
            'image': tag,
            'name': self.deployment_name,
            'namespace': self.kubectl.namespace,
            'replicas': replicas,
        }

        rendered = template.render(data=data)
        tmp_file = tempfile.NamedTemporaryFile(delete=False)

        tmp_file.write(rendered.encode('utf8'))

        return tmp_file.name
