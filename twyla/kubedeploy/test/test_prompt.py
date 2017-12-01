import unittest
import unittest.mock as mock
from twyla.kubedeploy.prompt import prompt, error_prompt


class TestPrompt(unittest.TestCase):
    def test_prompt(self):
        with mock.patch('sys.stdout') as mock_stdout:
            prompt('this is a test')

        mock_stdout.assert_has_calls([
            mock.call.write('\x1b[32m>> '),  # green prompt
            mock.call.write('this is a test'),
            mock.call.write('\n')  # newline added by print()
        ])

    def test_prompt_with_indentation(self):
        with mock.patch('sys.stdout') as mock_stdout:
            prompt('this is a test', indent=4)

        mock_stdout.assert_has_calls([
            mock.call.write('\x1b[32m>>     '),  # green prompt + indentation
            mock.call.write('this is a test'),
            mock.call.write('\n')  # newline added by print()
        ])

    def test_error_prompt(self):
        with mock.patch('sys.stdout') as mock_stdout:
            error_prompt('this is a test')

        mock_stdout.assert_has_calls([
            mock.call.write('\x1b[31m>> '),  # red prompt
            mock.call.write('this is a test'),
            mock.call.write('\n')  # newline added by print()
        ])

    def test_error_prompt_with_indentation(self):
        with mock.patch('sys.stdout') as mock_stdout:
            error_prompt('this is a test', indent=2)

        mock_stdout.assert_has_calls([
            mock.call.write('\x1b[31m>>   '),  # red prompt + indentation
            mock.call.write('this is a test'),
            mock.call.write('\n')  # newline added by print()
        ])
