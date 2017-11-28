[![Build Status](https://travis-ci.org/TwylaHelps/twyla.kubedeploy.svg?branch=master)](https://travis-ci.org/TwylaHelps/twyla.kubedeploy)

# twyla.kubedeploy

`kubedeploy` is glue tooling around Docker and the Kubernetes API to make build
and deployment of container based microservices quick and painless.

The two main purposes of `kubedeploy` are building Docker images based on the
local or remote state of the git repository of the microservice, pushing those
images to a registry, and deploying the image to a Kubernetes cluster based on a
deployment configuration that exists also either locally or remotely on the
cluster.

> NOTE: This tool is a work in progress moving the internal Twyla specific
> tooling to open source. The interface will likely change. Currently the tool
> will require a `requirements.txt` in the directory it is called from, making
> it seemingly only support Python services.


## Install

The recommended way to install is currently by checking out and installing with
pip into a previously created virtual environment.

    git clone https://github.com/TwylaHelps/twyla.kubedeploy
    cd twyla.kubedeploy
    pip install -r requirements.txt


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

### Deploying A Service

By default the deployment will be done based on an existing deployment. Only the
image will be updated just like running `kubectl edit deployment <name>` and
replacing the image.

In case no deployment exists a file `deployment.yml` in the current working
directory will be used as base, the image and namespace will be updated, and the
result will be sent to the Kubernetes API. The result is the same as calling
`kubectl apply -f <result>`. To make sure the deployment is correct use the
`--dry` switch first.

    $ kubedeploy deploy --registry <your-registry-domain> \
                        --image <service> \
                        --dry


## Known Bugs

- limited keyring support (should work on MacOS though)


## Todo

- [ ] improve test coverage
- [ ] support config files additionally to command line knobs
- [ ] test calls to APIs with `responses`
- [ ] rethink interface for printing messages
- [ ] dump deployments for use with `kubectl apply -f`
- [ ] add support for Kubernetes objects other than `Deployment`


## Whishlist

- [ ] support `rkt`
- [ ] support non-Python services when building images
