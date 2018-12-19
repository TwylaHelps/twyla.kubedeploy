import base64
import json
import os
from subprocess import PIPE, STDOUT, Popen

import docker
import docker_registry_client as registry
from requests import HTTPError

from twyla.kubedeploy.prompt import prompt

MACOS_KEYCHAIN_CMD = ['security', 'find-internet-password', '-l',
                      'Docker Credentials', '-w', '-s']


class DockerException(Exception):
    pass


def make_tag(registry: str, name: str, version: str) -> str:
    return "{}/{}:{}".format(registry, name, version)


def tag_components(tag: str) -> (str, str, str):
    domain, rest = tag.split('/', 1)
    repository, version = rest.split(':', 1)

    return domain, repository, version


def get_macos_credentials(domain):
    keychain_cmd = ["docker-credential-osxkeychain", "get"]
    p = Popen(keychain_cmd, stdout=PIPE, stdin=PIPE, stderr=STDOUT)
    credentials_json, _ = p.communicate(input=domain.encode('utf-8'))
    credentials = json.loads(credentials_json.decode('utf-8'))
    return credentials['Username'], credentials['Secret']


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
    if domain_part not in docker_auth_data['auths']:
        raise DockerException("Not authorized for registry {}".format(domain_part))

    if docker_auth_data.get('credsStore', '') == 'osxkeychain':
        username, password = get_macos_credentials(domain_part)
    else:
        base64_credentials = docker_auth_data['auths'][domain_part]['auth']
        # dXNlcm5hbWU6cGFzc3dvcmQK= -> username:password
        credentials = base64.b64decode(base64_credentials).decode('utf8')
        # username:password -> [username, password]
        username, password = credentials.split(':', 1)
    client = registry.DockerRegistryClient("https://{}".format(domain_part),
                                           username=username,
                                           password=password)
    repository = client.repository(repository)

    try:
        repository.manifest(version)
        return True
    except HTTPError as e:
        if e.response.status_code != 404:
            raise

    return False
