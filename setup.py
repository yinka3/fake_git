from setuptools import setup

setup(
    name = "fake-git",
    version = "0.0.1",
    packages = ["fake_git"],
    entry_points = {
        "console_scripts": [
            "fake-git = fake_git.cli:main",
        ]
    }
)


