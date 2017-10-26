import base64
import json
import os
import shutil
import sys
import tempfile
from typing import Callable

import click
import colorama
import docker
import kubernetes
import pip

import docker_registry_client as registry
import git


class Kube:
    def __init__(self,
                 namespace: str,
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
        self.environment = None

    def get_deployment(self):
        is_new = False
        deployment_name = '???'
        try:
            res = self.ext_v1_beta_client.read_namespaced_deployment(
                name=deployment_name,
                namespace=self.namespace)
            return res, is_new
        except kubernetes.client.rest.ApiException as e:
            # Create a new deployment if no existing is found
            if e.status == 404:
                is_new = True
                return self.default_deployment(), is_new
            else:
                raise e

    def deploy(self, tag: str, environment: str):
        # Get current deployment and update the relevant information
        self.printer("Deploying {} to the {} environment"
                     .format(tag, environment))
        self.environment = environment
        deployment, is_new = self.get_deployment()
        deployment = fill_deployment_definition(deployment,
                                                tag)

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

            self.printer("Deployment successful. It may need some time to"
                         "propagate.")
        except kubernetes.client.rest.ApiException as e:
            self.error_printer(e)

    def info(self):
        kubernetes.config.load_kube_config()
        deployment, _ = self.get_deployment()
        self.print_deployment_info('current ???', deployment)

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

    def default_deployment(self):
        # NOTE: could be read from a file once this tool becomes a proper
        # module.
        default = """
        {
            "kind": "Deployment",
            "apiVersion": "extensions/v1beta1",
            "metadata": {
                "name": "???",
                "namespace": "???",
                "labels": {
                    "app": "???"
                }
            },
            "spec": {
                "replicas": 1,
                "template": {
                    "metadata": {
                        "labels": {
                            "app": "???"
                        }
                    },
                    "spec": {
                        "containers": [
                            {
                                "name": "???",
                                "image": "registry/service:version",
                                "imagePullPolicy": "Always"
                            }
                        ],
                        "restartPolicy": "Always",
                        "imagePullSecrets": [
                            {
                                "name": "???"
                            }
                        ]
                    }
                },
                "strategy": {
                    "type": "RollingUpdate",
                    "rollingUpdate": {
                        "maxUnavailable": "1",
                        "maxSurge": "1"
                    }
                }
            }
        }
        """

        api_client = kubernetes.client.ApiClient()

        # Be like Response, my friend!
        # Implements res.data to make the deserializer work.
        class Res:
            def __init__(self, data):
                self.data = data

        res = Res(data=default)

        return api_client.deserialize(res, 'ExtensionsV1beta1Deployment')

    class DeployException(Exception):
        pass


# Use a colorized prompt to differenciate output of this script from output
# that is generated by called programms and libraries
colorama.init(autoreset=True)
PROMPT = '>> '


def prompt(msg: str, indent: int=0):
    indentation = ' ' * indent
    sys.stdout.write(colorama.Fore.GREEN + PROMPT + indentation)
    print(msg)


def error_prompt(msg: str):
    sys.stdout.write(colorama.Fore.RED + PROMPT)
    print(msg)


def chdir_to_script():
    # Change working dir to current script directory
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    os.chdir(script_dir)

    prompt('Working in {}'.format(script_dir))


def download_requirements(force: bool=False):
    # Create temporary directory as download target for requirements then
    # download to this temporary directory and move it into the docker
    # context. The docker context is the current directory that can not be
    # used as initial destination as it itself is part of the requirements.txt
    dest = os.path.join(os.getcwd(), 'pip-cache')

    if os.path.isdir(dest):
        if not force:
            prompt('pip-cache exists. Skipping download of requirements.')
            return

        # Remove the existing pip-cache if any
        prompt('pip-cache exists. Removing for fresh download of '
               'requirements.')
        shutil.rmtree(dest)

    tmp = tempfile.mkdtemp()
    prompt('Downloading requirements.')
    with open('requirements.txt') as f:
        deps = [line for line in f if line.startswith('git+ssh')]
    pip.main(['download', '-q', '--dest', tmp, *deps])
    shutil.move(tmp, dest)


def make_tag(registry: str, name: str, version: str) -> str:
    return "{}/{}:{}".format(registry, name, version)


def tag_components(tag: str) -> (str, str, str):
    domain, rest = tag.split('/', 1)
    repository, version = rest.split(':', 1)

    return domain, repository, version


def docker_image(op: str, tag: str):
    # The registry part of the tag will be used to determine the push
    # destination domain.
    client = docker.from_env(version='1.24')

    if op == "build":
        prompt('Building image: {}'.format(tag))
        client.images.build(tag=tag, path=os.getcwd())
    elif op == "push":
        prompt('Pushing image: {}'.format(tag))
        client.images.push(tag)


def docker_image_exists(tag: str) -> bool:
    # This one assumes a logged in local docker to read the credentials from
    home = os.path.expanduser('~')
    docker_auth_file = os.path.join(home, '.docker', 'config.json')
    with open(docker_auth_file) as fd:
        docker_auth_data = json.load(fd)

    # Extract the credentials for the docker json.
    domain_part, repository, version = tag_components(tag)
    base64_credentials = docker_auth_data['auths'][domain_part]['auth']
    # dXNlcm5hbWU6cGFzc3dvcmQK= -> username:password
    credentials = base64.b64decode(base64_credentials).decode('utf8')
    # username:password -> [username, password]
    username, password = credentials.split(':', 1)

    client = registry.DockerRegistryClient("https://{}".format(domain_part),
                                           username=username,
                                           password=password)

    return version in client.repository(repository).tags()


def fill_deployment_definition(
        deployment: kubernetes.client.ExtensionsV1beta1Deployment,
        tag: str):
    deployment_name = '???'

    # Set name
    deployment.metadata.name = deployment_name
    deployment.spec.template.metadata.labels['name'] = deployment_name
    deployment.spec.revisionHistoryLimit = 5

    # Set image. For now just grab the first container as there is only one
    # TODO: find a way to properly decide on the container to update here
    deployment.spec.template.spec.containers[0].image = tag

    return deployment


def head_of(branch: str=None, local: bool=False) -> str:
    repo = git.Repo('.')
    if branch is None:
        try:
            branch = repo.active_branch
        # The type error gets thrown for example on detached HEAD states and
        # during unfinished rebases and cherry-picks.
        except TypeError as e:
            error_prompt('No branch given and current status is inconclusive: '
                         '{}'.format(str(e)))
            sys.exit(1)

    if local:
        return repo.git.rev_parse(repo.head.commit, short=8)

    prompt("Getting remote HEAD of {}".format(branch))

    # Fetch all remotes (usually one?!) to make sure the latest refs are known
    # to git. Save remote refs that match current branch to make sure to avoid
    # ambiguities and bail out if a branch exists in multiple remotes with
    # different HEADs.
    remote_refs = []
    for remote in repo.remotes:
        remote.fetch()
        for ref in remote.refs:
            # Finding the remote tracking branch this way is a simplification
            # already that assumes the remote tracking branches are of the
            # format refs/remotes/foo/bar (indicating that it tracks a branch
            # named bar in a remote named foo), and matches the right-hand-side
            # of a configured fetch refspec. To actually do it correctly
            # involves reading local git config and use `git remote show
            # <remote-name>`. The main issue with that approach is it would
            # involve porcelain commands as there are no plumbing commands
            # available to get the remote tracking branches currently. Long
            # story short: follow the conventions and this script will work.
            if ref.name == '{remote}/{branch}'.format(remote=remote.name,
                                                      branch=branch):
                prompt('Found "{}" at {}'.format(ref.name,
                                                 str(ref.commit)[:8]))
                remote_refs.append(ref)

    # Bail out if no remote tracking branches where found.
    if len(remote_refs) < 1:
        error_prompt('No remote tracking branch matching "{}" found'.format(
            branch))
        sys.exit(1)

    # Iterate over found remote tracking branches and compare commit IDs; bail
    # out if there is more than one and they differ.
    if len(remote_refs) > 1:
        seen = {}
        for ref in remote_refs:
            seen[repo.git.rev_parse(ref.name)] = True
        if seen.keys() != 1:
            error_prompt('Multiple matching remote tracking branches with'
                         ' different commit IDs found. Can not go on. Make'
                         ' sure requested deployments are inambiguous.')
            sys.exit(1)

    # At this point the head commit of the first remote tracking branch can be
    # returned as it is the same as the others if they exist.
    return repo.git.rev_parse(remote_refs[0].commit, short=8)


@click.group()
@click.pass_context
def cli(ctx: click.Context):
    ctx.obj = {}


@cli.command()
@click.option('--registry', default='???')
@click.option('--image', default='???')
@click.option('--branch', help='The git branch to deploy. Defaults to master.',
              default='master')
@click.option('--version', help='Version of API to build and deploy. Will'
              'replace if it already exists.')
@click.option('--environment', default='???')
@click.option('--dry/--no-dry', help='Run without building, pushing, and'
              ' deploying anything',
              default=False)
@click.option('--local/--no-local', help='If set then the local state of the'
              ' service will be used to create, push, and deploy a Docker'
              ' image.',
              default=False)
@click.pass_obj
def deploy(kube: Kube, registry: str, image: str, branch: str, version: str,
           environment: str, local: bool, dry: bool):
    if local:
        # Reset branch when using local.
        branch = None

    chdir_to_script()
    if version is None:
        version = head_of(branch, local=local)

    kube = Kube(namespace='???',
                printer=prompt,
                error_printer=error_prompt)
    tag = make_tag(registry, image, version)

    if local and not dry:
        download_requirements()
        docker_image('build', tag)
        docker_image('push', tag)

    if not docker_image_exists(tag):
        error_prompt('Image not found: {}'.format(tag))
        if not dry:
            sys.exit(1)

    kube.info()

    if dry:
        prompt('Dry run finished. Not deploying.')
        return

    kube.deploy(tag, environment)


@cli.command()
@click.option('--registry', default='???')
@click.option('--image', default='???')
@click.option('--version', help='Version of API to build. Will replace if it'
              ' already exists.', default=None)
def build(registry: str, image: str, version: str):
    if version is None:
        version = head_of(None, local=True)

    tag = make_tag(registry, image, version)
    download_requirements()
    docker_image('build', tag)


@cli.command()
@click.option('--registry', default='???')
@click.option('--image', default='???')
@click.option('--version', help='Git commit ID or branch to build and deploy.'
              ' Will replace if it already exists.', default=None)
def push(registry: str, image: str, version: str):
    if version is None:
        version = head_of(None, local=True)

    tag = make_tag(registry, image, version)
    docker_image('push', tag)


@cli.command()
@click.pass_obj
def info(kube: Kube):
    kube = Kube(namespace='???',
                printer=prompt,
                error_printer=error_prompt)
    kube.info()


def main():
    cli(obj={})


if __name__ == '__main__':
    main()
