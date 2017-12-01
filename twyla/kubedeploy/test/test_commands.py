import os
import traceback
import unittest
from unittest import mock

from click.testing import CliRunner
from twyla import kubedeploy

REQUIREMENTS = '''
some_package==1.2.3
another_package==3.2.1
git+ssh://git_package==0.0.1
'''


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


    @mock.patch('twyla.kubedeploy.docker_helpers.open',
                new=mock.mock_open(read_data=REQUIREMENTS))
    @mock.patch('twyla.kubedeploy.pip')
    @mock.patch('twyla.kubedeploy.os')
    @mock.patch('twyla.kubedeploy.prompt')
    @mock.patch('twyla.kubedeploy.tempfile')
    @mock.patch('twyla.kubedeploy.shutil')
    def test_download_requirements_none(self,
                                        mock_shutil,
                                        mock_tempfile,
                                        mock_prompt,
                                        mock_os,
                                        mock_pip):
        mock_os.path.isfile.return_value = False

        kubedeploy.download_requirements()

        mock_os.path.join.assert_not_called()


    @mock.patch('twyla.kubedeploy.docker_helpers.open',
                new=mock.mock_open(read_data=REQUIREMENTS))
    @mock.patch('twyla.kubedeploy.pip')
    @mock.patch('twyla.kubedeploy.os')
    @mock.patch('twyla.kubedeploy.prompt')
    @mock.patch('twyla.kubedeploy.tempfile')
    @mock.patch('twyla.kubedeploy.shutil')
    def test_download_requirements_cache_exists(self,
                                                mock_shutil,
                                                mock_tempfile,
                                                mock_prompt,
                                                mock_os,
                                                mock_pip):
        mock_os.path.isfile.return_value = True
        mock_os.path.isdir.return_value = True
        mock_os.path.join.return_value = 'some/joined/path'

        kubedeploy.download_requirements()

        mock_os.path.join.assert_called_once_with(mock.ANY, 'pip-cache')
        mock_os.path.isdir.assert_called_once_with(mock.ANY)
        mock_prompt.assert_called_once_with(
            'pip-cache exists. Skipping download of requirements.')
        mock_tempfile.mkdtemp.assert_not_called()


    @mock.patch('twyla.kubedeploy.docker_helpers.open',
                new=mock.mock_open(read_data=REQUIREMENTS))
    @mock.patch('twyla.kubedeploy.pip')
    @mock.patch('twyla.kubedeploy.os')
    @mock.patch('twyla.kubedeploy.prompt')
    @mock.patch('twyla.kubedeploy.tempfile')
    @mock.patch('twyla.kubedeploy.shutil')
    def test_download_requirements(self,
                                   mock_shutil,
                                   mock_tempfile,
                                   mock_prompt,
                                   mock_os,
                                   mock_pip):
        mock_os.path.isfile.return_value = True
        mock_os.path.isdir.return_value = False
        mock_os.path.join.return_value = 'some/joined/path'

        kubedeploy.download_requirements()

        mock_tempfile.mkdtemp.assert_called_once_with()
        mock_prompt.assert_called_once_with('Downloading requirements.')
        mock_pip.main.assert_called_once_with(
            ['download', '-q', '--dest', mock_tempfile.mkdtemp.return_value])
        mock_shutil.move.assert_called_once_with(
            mock_tempfile.mkdtemp.return_value,
            'some/joined/path')


    @mock.patch('twyla.kubedeploy.docker_helpers.open',
                new=mock.mock_open(read_data=REQUIREMENTS))
    @mock.patch('twyla.kubedeploy.pip')
    @mock.patch('twyla.kubedeploy.os')
    @mock.patch('twyla.kubedeploy.prompt')
    @mock.patch('twyla.kubedeploy.tempfile')
    @mock.patch('twyla.kubedeploy.shutil')
    def test_download_requirements_force(self,
                                         mock_shutil,
                                         mock_tempfile,
                                         mock_prompt,
                                         mock_os,
                                         mock_pip):
        mock_os.path.isfile.return_value = True
        mock_os.path.isdir.return_value = True
        mock_os.path.join.return_value = 'some/joined/path'

        kubedeploy.download_requirements(force=True)

        mock_os.path.join.assert_called_once_with(mock.ANY, 'pip-cache')
        mock_os.path.isdir.assert_called_once_with(mock.ANY)
        mock_prompt.assert_has_calls([
            mock.call(
                'pip-cache exists. Removing for fresh download of requirements.'),
            mock.call('Downloading requirements.'),
        ])

        mock_pip.main.assert_called_once_with(
            ['download', '-q', '--dest', mock_tempfile.mkdtemp.return_value])
        mock_shutil.move.assert_called_once_with(
            mock_tempfile.mkdtemp.return_value,
            'some/joined/path')
