#!/usr/bin/env python
import os
import sys

import django
from django.conf import settings
from django.test.utils import get_runner

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

def run_settings():
    settings.configure(
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

        MIDDLEWARE_CLASSES = []
    )
if __name__ == "__main__":
    run_settings()
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(["tests"])
    sys.exit(bool(failures))