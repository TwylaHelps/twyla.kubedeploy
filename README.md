[![Build Status](https://travis-ci.org/TwylaHelps/twyla.kubedeploy.svg?branch=master)](https://travis-ci.org/TwylaHelps/twyla.kubedeploy)
[![codecov](https://codecov.io/gh/TwylaHelps/twyla.kubedeploy/branch/master/graph/badge.svg)](https://codecov.io/gh/TwylaHelps/twyla.kubedeploy)

# twyla.kubedeploy

`kubedeploy` is glue tooling around Docker and the Kubernetes API to make build
and deployment of container based microservices quick and painless.

The two main purposes of `kubedeploy` are building Docker images based on the
local or remote state of the git repository of the microservice, pushing those
images to a registry, and deploying the image to a Kubernetes cluster based on a
deployment configuration that exists also either locally or remotely on the
cluster.


## Install

    pip install git+https://github.com/TwylaHelps/twyla.kubedeploy


## Usage

### Preconditions

To make use of the `kubedeploy` tool you have to have [Docker](www.docker.com)
installed and running to build images. To push images either an official Docker
registry account is required or a private registry has to exist. You need to be
logged into your Docker registry already. If you want to deploy images you also
have to have a running Kubernetes cluster available and configured (check out
[minikube](kubernetes.io/docs/getting-started-guides/minikube/) to run
Kubernetes locally).


All commands that operate on a Kubernetes cluster will use the currently set
config and context.

### Versioning

If no explicit version for images gets passed in as parameter the short git
commit ID of HEAD of the `master` branch will be used.

### Creating Docker Images

The Docker images will be created from the current local state of the project.
This task is supposed to be done by a CI/CD system when running production
builds.

From the directory that contains your `Dockerfile` run:

    $ kubedeploy build --registry <your-registry-domain> \
                       --image <service>

The `--image` and `--registry` parameters are required and will determine the
tag of the built image of the format `<registry>/<image>:<version>`.

### Pushing Docker Images

Pushing the image is similar to building it, the registry name and image name
have to be passed in, the version will be determined from the current git state.

    $ kubedeploy push --registry <your-registry-domain> \
                      --image <service>

To successfully push the user running the command has to be logged into the
registry already.

### Getting Deployment Info

To get information about the currently deployed image for a particular deployment name, namespace, cluster run:

    $ kubedeploy info --name <deployment-name>

The namespace will default to `default`.

### Deployment templates

The template format is Jinja2 and the configuration is being made available as
`data` dictionary. Example data structure:

    data = {
        'name': 'mydeployment',
        'namespace': 'default',
        'image': 'my-registry/myimage:version',
        'replicas': 10,
        'variants': ['de', 'en']
    }

Example template:

    apiVersion: v1
    kind: Deployment
    metadata:
      labels:
        app: {{ data.name }}
      namespace: {{ data.namespace }}
    template:
      spec:
        replicas: {{ data.replicas if data.replicas else 10 }}
        ...

### Deploying A Service

By default the deployment will be done based on an existing deployment. Only the
image will be updated just like running `kubectl edit deployment <name>` and
replacing the image.

Deployments will be created from a file `deployment.yml` in the current working
directory, and the result will be sent to the Kubernetes API. The result is the
same as calling `kubectl apply -f <result>`. To make sure the deployment is
correct use the `--dry` switch first.

    $ kubedeploy deploy --registry <your-registry-domain> \
                        --image <service> \
                        --dry

### Replicating Deployment Versions

To replicate versions of deployments to another cluster `kubedeploy` provides a
way to dump and apply a list of deployments selected by label.

    $ kubedeploy cluster_info --namespace twyla \
                              --group front-end \
                              --dump-to demo.yml

This command will dump the definitions of all deployments with a label
`servicegroup` of `front-end` to the file `demo.yml`. The objects will be
scrubbed of cluster specific information like status and object history.

It can be applied to a different cluster after switching the Kubernetes context
or configuration.

    $ kubedeploy apply --from-file demo.yml

This will apply the list to the other cluster. The count of replicas will be
preserved on the target cluster if the deployment exists.

### Configuration Files

All examples until here used command line arguments to configure the behavior of
`kubedeploy`. To make the work flow more convenient when using the tool a lot,
configuration files can be used.

By convention `kubedeploy` looks for a file named `kubedeploy.yml` in the
working directory and loads it before parsing the command line arguments. The
configuration is a list of key-value pairs in YAML format where the names of the
keys are equivalent to the command line argument names.

The following command line arguments can be used in the configuration file:

    --name
    --namespace
    --image
    --registry
    --group
    --branch
    --version

Some arguments have to be used explicitly still:

    --local
    --dry
    --dump-to
    --from-file

Example:

    # Name of the Kubernetes deployment
    name: my-service
    # Namespace in Kubernetes
    namespace: default
    # Registry and image names. Will be combined to:
    # my-private-reg/service-one:<generated-version>
    registry: my-private-reg
    image: service-one
    group: twyla


## Known Bugs

- limited keyring support (should work on MacOS though)

## Todo

- [x] improve test coverage
- [ ] rethink interface for printing messages
- [x] dump deployments for use with `kubectl apply -f`
- [x] support multi-document `deployment.yml` so other objects can be added (e.g. acompanying services)


## Whishlist

- [x] support config files additionally to command line knobs
- [ ] support `rkt`
- [x] support non-Python services when building images
