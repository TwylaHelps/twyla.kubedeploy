import unittest
from unittest import mock
from types import SimpleNamespace as Bunch

import pytest

from twyla import kubedeploy


class HeadOfTests(unittest.TestCase):

    @mock.patch('twyla.kubedeploy.git')
    def test_local(self, mock_git):
        """If local is True, head of local should be returned"""
        head = kubedeploy.head_of('/blah', local=True)
        rev_parse = mock_git.Repo.return_value.git.rev_parse
        assert head is rev_parse.return_value
        assert rev_parse.called_once_with(mock_git.Repo.return_value.head.commit,
                                          short=8)
        mock_git.Repo.assert_called_once_with('/blah')


    @mock.patch('twyla.kubedeploy.error_prompt')
    @mock.patch('twyla.kubedeploy.git')
    def test_no_matching_remote(self, mock_git, mock_error_prompt):
        repo = mock_git.Repo.return_value
        repo.active_branch = 'the-branch'
        remote = mock.MagicMock()
        remote.refs = [Bunch(name='', commit='')]
        repo.remotes = [remote]
        with pytest.raises(SystemExit):
            head = kubedeploy.head_of('/blah')
        mock_error_prompt.assert_called_once_with(
            'No remote tracking branch matching "the-branch" found')


    @mock.patch('twyla.kubedeploy.error_prompt')
    @mock.patch('twyla.kubedeploy.git')
    def test_matching_remote(self, mock_git, mock_error_prompt):
        repo = mock_git.Repo.return_value
        repo.active_branch = 'the-branch'
        remote = mock.MagicMock()
        remote.name = 'origin'
        remote.refs = [Bunch(name='origin/the-branch', commit='githash-remote')]
        repo.remotes = [remote]
        head = kubedeploy.head_of('/blah')
        assert head == repo.git.rev_parse.return_value
