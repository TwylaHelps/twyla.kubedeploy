from setuptools import setup

dependencies = ['click', 'colorama', 'docker',
                'kubernetes', 'docker-registry-client', 'GitPython', 'pyyaml']

setup(
    name="twyla.kubedeploy",
    version="0.0.1",
    author="Twyla Devs",
    author_email="dev@twylahelps.com",
    description=("Twyla Kubernetes Deploy"),
    install_requires=dependencies,
    extras_require={
        'test': ['pytest'],
    },
    packages=["twyla.kubedeploy"],
    entry_points={
        'console_scripts': [
            'kubedeploy = twyla.kubedeploy:deploy'
        ]
    },
    url="https://bitbucket.org/twyla/twyla.kubedeploy",
)
