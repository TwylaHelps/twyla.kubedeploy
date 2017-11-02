[![Build Status](https://travis-ci.org/TwylaHelps/twyla.kubedeploy.svg?branch=master)](https://travis-ci.org/TwylaHelps/twyla.kubedeploy)

# twyla.kubedeploy

This script is a prototype of a deployment tool targeting Kubernetes
clusters. The main purpose of this is to gather experience deploying and
managing services on Kubernetes.

This uses the default builtin rolling update strategy of Kubernetes.

TODOs for the implementation as stand-alone tool:
- properly test all components
- testing strategy for the calls to the Kubernetes API
- remove hard coded information like the registry secret name, etc.
- rethink interface for printing messages