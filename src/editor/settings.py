"""
Django settings for Names Registry Editor project.

Generated by 'django-admin startproject' using Django 3.1.5.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.1/ref/settings/
"""

import configparser
from pathlib import Path
import sys

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

try:
    with open(BASE_DIR / '..' / 'VERSION', 'r') as f:
        VERSION = f.read()
except FileNotFoundError:
    VERSION = 'unknown'

# User-configurable settings are located in the following files.
# Files appearing *later* in the list override earlier files.
CONFIG_FILES = [
    '/etc/ddr/namesdbeditor.cfg',
    '/etc/ddr/namesdbeditor-local.cfg'
]
config = configparser.ConfigParser()
configs_read = config.read(CONFIG_FILES)
if not configs_read:
    print(f'Cannot read config files! {CONFIG_FILES}')
    sys.exit(1)

# ----------------------------------------------------------------------

DEBUG = config.get('debug', 'debug')

WSGI_APPLICATION = 'editor.wsgi.application'

# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/opt/namesdb-editor/db/django.db',
    },
    'names': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': config.get('database', 'name'),
    }
}

DATABASE_ROUTERS = ['names.models.NamesRouter']

DOCSTORE_HOSTS = config.get('database', 'namesdb_host')

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/
STATIC_ROOT = config.get('media', 'static_root')
STATIC_URL = config.get('media', 'static_url')

# ----------------------------------------------------------------------

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = [
    host.strip()
    for host in config.get('security', 'allowed_hosts').strip().split(',')
]

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config.get('security', 'secret_key')

ADMINS = (
    ('Geoff Froh', 'geoff.froh@densho.org'),
    ('Geoffrey Jost', 'geoffrey.jost@densho.org'),
)
MANAGERS = ADMINS

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    #
    'editor',
    'names',
    'namesdb_public',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'editor.urls'

# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/
TIME_ZONE = 'America/Los_Angeles'
LANGUAGE_CODE = 'en-us'
USE_I18N = False
USE_L10N = False
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
