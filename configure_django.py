import os

import django


# https://stackoverflow.com/a/22722410/13186004
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "evolution.settings")
django.setup()
