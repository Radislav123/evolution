"""
Django settings for evolution project.

Generated by "django-admin startproject" using Django 4.1.3.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.1/ref/settings/
"""

from pathlib import Path


# Build paths inside the project like this: BASE_DIR / "subdir".
BASE_DIR = Path(__file__).resolve().parent.parent

LOGS_PATH = Path(f"{BASE_DIR}/logs")

# изображения, звуки...
RESOURCES_PATH = f"{BASE_DIR}/resources"
IMAGES_PATH = f"{RESOURCES_PATH}/images"

CREATURE_IMAGE_PATH = f"{IMAGES_PATH}/BaseCreature.png"
IMAGES_STORE_FORMAT = "RGBA"

# файлы описаний
DESCRIPTIONS_PATH = "resources/object_description"
WORLD_RESOURCE_DESCRIPTIONS_PATH = f"{DESCRIPTIONS_PATH}/world_resource"
WORLD_DESCRIPTIONS_PATH = f"{DESCRIPTIONS_PATH}/world"
CREATURE_DESCRIPTIONS_PATH = f"{DESCRIPTIONS_PATH}/creature"
GENOME_DESCRIPTIONS_PATH = f"{CREATURE_DESCRIPTIONS_PATH}/genome"
CHROMOSOME_DESCRIPTIONS_PATH = f"{GENOME_DESCRIPTIONS_PATH}/chromosome"
GENE_INTERFACE_DESCRIPTIONS_PATH = f"{CHROMOSOME_DESCRIPTIONS_PATH}/gene_interface"
GENE_DESCRIPTIONS_PATH = f"{CHROMOSOME_DESCRIPTIONS_PATH}/gene"
BODYPART_INTERFACE_DESCRIPTIONS_PATH = f"{CREATURE_DESCRIPTIONS_PATH}/bodypart_interface"
BODYPART_DESCRIPTIONS_PATH = f"{CREATURE_DESCRIPTIONS_PATH}/bodypart"
ACTION_DESCRIPTIONS_PATH = f"{CREATURE_DESCRIPTIONS_PATH}/action"

# tps - ticks per second
MAX_TPS = 1000

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-%l1uoeh!mh!qat$m3l@p1hj*s%zt1iy3om98v7kbtobf^)bt-s"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "core",
    "simulator",
    "player",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "evolution.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "evolution.wsgi.application"

# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "evolution",
        "USER": "postgres",
        "PASSWORD": "password",
        "HOST": "localhost",
        "PORT": "5432",
    }
}

# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/
STATIC_URL = "static/"

# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
