import os

import django.conf


# https://stackoverflow.com/a/22722410/13186004
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "evolution.settings")
if not django.conf.settings.configured:
    django.setup()
