import os
import traceback
import unittest
from unittest import mock

from click.testing import CliRunner
from twyla import kubedeploy


class DeployCommandTests(unittest.TestCase):

    @mock.patch('twyla.kubedeploy.docker_helpers.docker_image_exists')
    @mock.patch('twyla.kubedeploy.Kube')
    @mock.patch('twyla.kubedeploy.head_of')
    def test_deploy_master_head(self, mock_head_of, mock_Kube,
                                mock_docker_exists):
        """When passed no arguments, the deploy command deploys head of
        master"""
        mock_head_of.return_value = 'githash'
        mock_docker_exists.return_value = True
        runner = CliRunner()
        result = runner.invoke(kubedeploy.deploy, ['--registry',
                                                   'myown.private.registry',
                                                   '--image',
                                                   'test-service',
                                                   '--name',
                                                   'test-deployment',
                                                   '--namespace',
                                                   'anamespace'])
        if result.exception:
            print(''.join(traceback.format_exception(*result.exc_info)))
            self.fail()

        # Default branch is master, and local is False
        mock_head_of.assert_called_once_with(os.getcwd(),
                                             'master',
                                             local=False)
        mock_Kube.assert_called_once_with(
            namespace='anamespace',
            deployment_name='test-service',
            printer=kubedeploy.prompt,
            error_printer=kubedeploy.error_prompt)
        kube = mock_Kube.return_value
        kube.deploy.assert_called_once_with(
            'myown.private.registry/test-service:githash'
        )


    @mock.patch('twyla.kubedeploy.docker_helpers.docker_image_exists')
    @mock.patch('twyla.kubedeploy.Kube')
    @mock.patch('twyla.kubedeploy.head_of')
    def test_abort_on_no(self,
                         mock_head_of,
                         mock_Kube,
                         mock_docker_exists):
        """
        On dry runs no deployment should be done.
        """
        mock_head_of.return_value = 'githash'
        mock_docker_exists.return_value = True
        runner = CliRunner()
        result = runner.invoke(kubedeploy.deploy, ['--registry',
                                                   'myown.private.registry',
                                                   '--image',
                                                   'test-service',
                                                   '--name',
                                                   'test-deployment',
                                                   '--namespace',
                                                   'anamespace',
                                                   '--dry'])
        if result.exception:
            print(''.join(traceback.format_exception(*result.exc_info)))
            self.fail()
        kube = mock_Kube.return_value
        assert kube.deploy.call_count == 0



    @mock.patch('twyla.kubedeploy.error_prompt')
    @mock.patch('twyla.kubedeploy.docker_helpers.docker_image_exists')
    @mock.patch('twyla.kubedeploy.Kube')
    @mock.patch('twyla.kubedeploy.head_of')
    def test_abort_on_missing_image(self, mock_head_of, mock_Kube,
                                    mock_docker_exists, mock_error_prompt):
        """
        If the image does not exist in the registry then no deployment should
        be done.
        """
        mock_head_of.return_value = 'githash'
        mock_docker_exists.return_value = False
        runner = CliRunner()
        runner.invoke(kubedeploy.deploy, ['--registry',
                                          'myown.private.registry',
                                          '--image',
                                          'test-service',
                                          '--name',
                                          'test-deployment',
                                          '--namespace',
                                          'anamespace'])
        # Not checking for the exception on result.exception here,
        # because SystemExit is validly raised for sys.exit(1) on
        # missing image
        kube = mock_Kube.return_value
        assert kube.deploy.call_count == 0
        assert mock_error_prompt.call_count == 1
        mock_error_prompt.assert_called_once_with(
            "Image not found: myown.private.registry/test-service:githash")
