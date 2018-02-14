import functools
import json
import subprocess

import yaml


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
        print(' '.join(command))
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


    def _list_entities(self, entity, selectors=None, expect_json=True):
        args = ['get', entity]
        args.extend(self._make_selector_args(selectors))

        if expect_json:
            args.extend(['-o', 'json'])
        return self._call(self._make_command(args))


    def _make_selector_args(self, selectors):
        if selectors is None:
            return []

        # {'key1': 'value1', 'key2': 'value2'}
        selector_strings = []
        for k, v in selectors.items():
            # ['key1value1', 'key2=value2']
            selector_strings.append('='.join([k, v]))

        if selector_strings:
            return ['--selector', ','.join(selector_strings)]

        return []


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


    def update_replicas(self, kube_list):
        for deployment in kube_list['items']:
            namespace = deployment['metadata'].get('namespace') or 'default'
            name = deployment['metadata']['name']

            # NOTE: Setting the namespace for every deployment currently makes
            # limited sense as only one namespace is supported for dumping the
            # file in the first place. It is nontheless required at least once.
            self.namespace = namespace
            remote = json.loads(self.get_deployment(name))

            deployment['spec']['replicas'] = remote['spec']['replicas']
