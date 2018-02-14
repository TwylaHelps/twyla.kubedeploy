import copy
import os
import shutil
import sys
import tempfile

import click
import git
import pip
import yaml

from twyla.kubedeploy import docker_helpers
from twyla.kubedeploy.kube import Kube
from twyla.kubedeploy.kubectl import Kubectl, KubectlCallFailed
from twyla.kubedeploy.prompt import error_prompt, prompt


def download_requirements(force: bool=False):
    if not os.path.isfile('requirements.txt'):
        return
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


def head_of(working_directory: str, branch: str=None, local: bool=False) -> str:
    repo = git.Repo(working_directory)
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
                         ' sure requested deployments are unambiguous.')
            sys.exit(1)

    # At this point the head commit of the first remote tracking branch can be
    # returned as it is the same as the others if they exist.
    return repo.git.rev_parse(remote_refs[0].commit, short=8)


@click.group()
@click.pass_context
def cli(ctx: click.Context):
    ctx.obj = {}


@cli.command()
@click.option('--registry', help='Docker registry name.', required=True)
@click.option('--image', help='Docker image name.',
              required=True)
@click.option('--name', help='Name of the deployment.',
              required=True)
@click.option('--namespace', help='The destination namespace in the cluster.',
              default='default')
@click.option('--branch', help='The git branch to deploy. Defaults to master.',
              default='master')
@click.option('--version', help='Version of API to build and deploy. Will'
              'replace if it already exists.')
@click.option('--dry/--no-dry', help='Run without building, pushing, and'
              ' deploying anything',
              default=False)
@click.option('--local/--no-local', help='If set then the local state of the'
              ' service will be used to create, push, and deploy a Docker'
              ' image.',
              default=False)
def deploy(registry: str, image: str, name: str, namespace: str, branch: str,
           version: str, local: bool, dry: bool):
    working_directory = os.getcwd()
    if local:
        # Reset branch when using local.
        branch = None
    if version is None:
        version = head_of(working_directory, branch, local=local)
    kube = Kube(namespace=namespace,
                deployment_name=image,
                printer=prompt,
                error_printer=error_prompt)
    tag = docker_helpers.make_tag(registry, image, version)
    if local and not dry:
        download_requirements()
        docker_helpers.docker_image('build', tag)
        docker_helpers.docker_image('push', tag)

    if not docker_helpers.docker_image_exists(tag):
        error_prompt('Image not found: {}'.format(tag))
        if not dry:
            sys.exit(1)

    kube.info()

    if dry:
        prompt('Dry run finished. Not deploying.')
        return

    kube.apply(tag)


@cli.command()
@click.option('--registry', help='Docker registry name.', required=True)
@click.option('--image', help='Docker image name.',
              required=True)
@click.option('--version', help='Version of API to build. Will replace if it'
              ' already exists.', default=None)
def build(registry: str, image: str, version: str):
    if version is None:
        version = head_of(None, local=True)

    tag = docker_helpers.make_tag(registry, image, version)
    download_requirements()
    docker_helpers.docker_image('build', tag)


@cli.command()
@click.option('--registry', help='Docker registry name.', required=True)
@click.option('--image', help='Docker image name.',
              required=True)
@click.option('--version', help='Git commit ID or branch to build and deploy.'
              ' Will replace if it already exists.', default=None)
def push(registry: str, image: str, version: str):
    if version is None:
        version = head_of(None, local=True)

    tag = docker_helpers.make_tag(registry, image, version)
    docker_helpers.docker_image('push', tag)


@cli.command()
@click.option('--name', help='Deployment name.', required=True)
@click.option('--namespace', help='Namespace in the cluster.',
              default='default')
def info(name: str, namespace: str):
    kube = Kube(namespace=namespace,
                deployment_name=name,
                printer=prompt,
                error_printer=error_prompt)
    kube.info()


@cli.command()
@click.option('--namespace', help='Namespace in the cluster.',
              default='default')
@click.option('--group',
              help='Value of the servicegroup selector to select by.',
              default='twyla')
@click.option('--dump-to',
              help='Dump cluster info into kubectl compatible yaml file',
              default=None)
def cluster_info(dump_to: str, group: str, namespace: str):
    kubectl = Kubectl()
    kubectl.namespace = namespace

    state = kubectl.list_deployments(selectors={'servicegroup': group})
    print_cluster_info(state)

    if dump_to is not None:
        deployable = scrub_cluster_info(state)
        with open(dump_to, mode='w') as fd:
            fd.write(yaml.dump(deployable, default_flow_style=False))


def scrub_cluster_info(state):
    '''
    scrub_cluster_info removes state information that is not required to deploy
    the cluster state to another cluster.
    '''
    deployable = {
        'apiVersion': 'v1',
        'kind': 'List',
        'metadata': {},
        'items': []
    }
    metadata_scrub = ['annotations', 'creationTimestamp',
                      'generation', 'resourceVersion',
                      'selfLink', 'uid']

    for item in state.get('items'):
        scrubbed_item = copy.deepcopy(item)
        if scrubbed_item.get('status') is not None:
            del scrubbed_item['status']

        for data in metadata_scrub:
            if scrubbed_item['metadata'].get(data) is not None:
                del scrubbed_item['metadata'][data]

        deployable['items'].append(scrubbed_item)

    return deployable


def print_cluster_info(state):
    for item in state['items']:
        name = item['metadata']['name']
        prompt(name)
        for cont in item['spec']['template']['spec']['containers']:
            prompt(cont['image'], 4)
        if item.get('status') is None:
            error_prompt('No replicas running.', 4)
        else:
            prompt(
                (f'replicas: {item["status"]["replicas"]} '
                 f'ready: {item["status"]["readyReplicas"]} '
                 f'updated: {item["status"]["updatedReplicas"]}'), 4)


@cli.command()
@click.option('--from-file',
              help='File containing a Kubernetes List of deployments',
              default=None)
def apply(from_file: str):
    # Load the deployments from file and get the current count of replicas in
    # the target cluster for each of the deployments. Then update the replicas
    # to match the target cluster. Save the file and pass on to kubectl apply.
    with open(from_file) as fd:
        content = fd.read()
    kube_list = yaml.load(content)

    kubectl = Kubectl()
    kubectl.update_replicas(kube_list)

    with open(from_file, mode='w') as fd:
        fd.write(yaml.dump(kube_list, default_flow_style=False))

    try:
        lines = kubectl.apply(from_file)
        for line in lines.split('\n'):
            prompt(line)
    except KubectlCallFailed as e:
        error_prompt(e)


def main():
    cli(obj={})


if __name__ == '__main__':
    main()
