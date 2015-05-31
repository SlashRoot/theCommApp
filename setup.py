from the_comm_app import __version__
import errno
import os
import sys
from setuptools import setup, find_packages


def file_name(rel_path):
    dir_path = os.path.dirname(__file__)
    return os.path.join(dir_path, rel_path)


def read(rel_path):
    with open(file_name(rel_path)) as f:
        return f.read()


def readlines(rel_path):
    with open(file_name(rel_path)) as f:
        ret = f.readlines()
    return ret


def mkdir_p(path):
    "recreate mkdir -p functionality"
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

share_path = os.path.join(
    os.path.dirname(sys.executable),
    'share/theCommApp'
)

mkdir_p(share_path)

setup(
    author="slashRoot Tech Collective",
    author_email="justin@justinholmes.com",
    name="theCommApp",
    packages=find_packages(),
    version=__version__,
    url="https://github.com/SlashRoot/theCommApp",
    description="Simple phone calls and sms for Python / hendrix.",
    # long_description=read('docs/index.md'),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
    ],
    keywords=["phone", "twisted", "async", "sms"],
    # install_requires=readlines('REQUIREMENTS')
)
