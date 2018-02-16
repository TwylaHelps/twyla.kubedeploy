from setuptools import setup

dependencies = [
    'click>=6.7',
    'colorama>=0.3.9',
    'docker>=2.6.1',
    'docker_registry_client>=0.5.2',
    'GitPython>=2.1.7',
    'Jinja2>=2.10',
    'PyYAML>=3.12',
    'requests>=2.18.4',
]

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
            'kubedeploy = twyla.kubedeploy:cli'
        ]
    },
    url="https://bitbucket.org/twyla/twyla.kubedeploy",
)
