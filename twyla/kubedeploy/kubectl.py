import json
import functools
import subprocess


class KubectlCallFailed(Exception):
    pass


class Kubectl:
    def __init__(self):
        self.exe = 'kubectl'
        self.namespace = None


    def _make_command(self, args=['get', 'pods']):
        cmd = []
        cmd.append(self.exe)

        if self.namespace:
            cmd.extend(['--namespace', self.namespace])

        cmd.extend(args)

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

        out = proc.stdout.decode('utf8')
        if expect_json:
            return json.loads(out)

        return out


    def apply(self, file_name):
        args = ['apply', '-f', file_name]
        return self._call(self._make_command(args), expect_json=False)


    def _get_entity_by_name(self, entity, name):
        args = ['get', entity, name, '-o', 'json']
        return self._call(self._make_command(args))


    def _list_entities(self, entity):
        args = ['get', entity, '-o', 'json']
        return self._call(self._make_command(args))


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
