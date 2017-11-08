import os
import unittest
from unittest import mock
import traceback

from click.testing import CliRunner

from twyla import kubedeploy

class DeployCommandTests(unittest.TestCase):

    @mock.patch('twyla.kubedeploy.input')
    @mock.patch('twyla.kubedeploy.docker_image_exists')
    @mock.patch('twyla.kubedeploy.Kube')
    @mock.patch('twyla.kubedeploy.head_of')
    @mock.patch('twyla.kubedeploy.load_options')
    def test_deploy_master_head(self, mock_load_options, mock_head_of, mock_Kube,
                                mock_docker_exists, mock_input):
        """When passed no arguments, the deploy command deploys head of
        master"""
        mock_load_options.return_value = {
            'registry': 'myown.private.registry',
            'service_name': 'test-service',
            'namespace': 'anamespace'
        }
        mock_head_of.return_value = 'githash'
        mock_docker_exists.return_value = True
        mock_input.return_value = 'y'
        runner = CliRunner()
        result = runner.invoke(kubedeploy.deploy)
        if result.exception:
            print(''.join(traceback.format_exception(*result.exc_info)))
            self.fail()
        assert mock_load_options.called_once_with(os.getcwd())
        # Default branch is master, and local is False
        mock_head_of.assert_called_once_with(os.getcwd(), 'master', local=False)
        mock_Kube.assert_called_once_with(
            namespace='anamespace',
            deployment_name='test-service',
            printer=kubedeploy.prompt,
            error_printer=kubedeploy.error_prompt)
        kube = mock_Kube.return_value
        kube.deploy.assert_called_once_with(
            'myown.private.registry/test-service:githash'
        )


    @mock.patch('twyla.kubedeploy.input')
    @mock.patch('twyla.kubedeploy.docker_image_exists')
    @mock.patch('twyla.kubedeploy.Kube')
    @mock.patch('twyla.kubedeploy.head_of')
    @mock.patch('twyla.kubedeploy.load_options')
    def test_abort_on_no(self, mock_load_options, mock_head_of, mock_Kube,
                         mock_docker_exists, mock_input):
        """When user enters something other than y or Y, deploy should be
        aborted.
        """
        mock_load_options.return_value = {
            'registry': 'myown.private.registry',
            'service_name': 'test-service',
            'namespace': 'anamespace'
        }
        mock_head_of.return_value = 'githash'
        mock_docker_exists.return_value = True
        mock_input.return_value = 'n'
        runner = CliRunner()
        result = runner.invoke(kubedeploy.deploy)
        if result.exception:
            print(''.join(traceback.format_exception(*result.exc_info)))
            self.fail()
        kube = mock_Kube.return_value
        assert kube.deploy.call_count == 0
