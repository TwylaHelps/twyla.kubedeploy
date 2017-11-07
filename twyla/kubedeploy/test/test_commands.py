import os
import unittest
from unittest import mock

from click.testing import CliRunner

from twyla import kubedeploy

class DeployCommandTests(unittest.TestCase):

    @mock.patch('twyla.kubedeploy.head_of')
    @mock.patch('twyla.kubedeploy.load_options')
    def test_deploy_master_head(self, mock_load_options, mock_head_of):
        """When passed no arguments, the deploy command deploys head of
        master"""
        mock_load_options.return_value = {
            'registry': 'twyla.kubedeploy.registry',
        }
        mock_head_of.return_value = 'githash'
        runner = CliRunner()
        result = runner.invoke(kubedeploy.deploy)
        assert mock_load_options.called_once_with(os.getcwd())
        # Default branch is master, and local is False
        assert mock_head_of.called_once_with('master', False)
