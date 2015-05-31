#!/usr/bin/env python
import os
import sys
import logging

import django
from django.conf import settings
from django.test.utils import get_runner



root = logging.getLogger()
root.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(message)s')
ch.setFormatter(formatter)
root.addHandler(ch)
logger = logging.getLogger(__name__)


BASE_DIR = os.path.dirname(os.path.dirname(__file__))


def run_settings():
    settings.configure(
        MIDDLEWARE_CLASSES=[],
        ROOT_URLCONF='tests.urls_for_tests',

        INSTALLED_APPS=[
            'the_comm_app',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            ],
        SECRET_KEY = "LLAMAS",

        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
            }
        },
    )
if __name__ == "__main__":
    run_settings()
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(["tests"])
    sys.exit(bool(failures))