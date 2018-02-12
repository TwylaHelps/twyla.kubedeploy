import json
import functools
import subprocess


class KubectlCallFailed(Exception):
    pass


class Kubectl:
    def __init__(self):
        self.exe = 'kubectl'
        self.args = [
            'get',
            'pods'
        ]
        self.namespace = None


    def _make_command(self):
        cmd = []
        cmd.append(self.exe)

        if self.namespace:
            cmd.extend(['--namespace', self.namespace])

        cmd.extend(self.args)

        return cmd


    def _call(self, command, expect_json=True):
        try:
            proc = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
            proc.check_returncode()
        except subprocess.CalledProcessError:
            raise KubectlCallFailed(proc.stderr)

        if expect_json:
            return json.loads(proc.stdout.decode('utf8'))

        return proc.stdout.decode('utf8')


    def apply(self, file_name):
        self.args = ['apply', '-f', file_name]
        return self._call(self._make_command(), expect_json=False)


    def _get_entity_by_name(self, entity, name):
        self.args = ['get', entity, name, '-o', 'json']
        return self._call(self._make_command())


    def _list_entities(self, entity):
        self.args = ['get', entity, '-o', 'json']
        return self._call(self._make_command())


    def __getattr__(self, attr):
        get = 'get_'
        _list = 'list_'
        if attr.startswith(get):
            return functools.partial(
                self._get_entity_by_name,
                attr[len(get):])
        elif attr.startswith(_list):
            return functools.partial(
                self._list_entities,
                attr[len(_list):])
