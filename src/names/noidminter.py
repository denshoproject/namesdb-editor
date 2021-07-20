import requests

from django.conf import settings


def get_noid():
    r = requests.post(
        settings.NOIDMINTER_URL,
        auth=(settings.NOIDMINTER_USERNAME, settings.NOIDMINTER_PASSWORD)
    )
    if r.status_code != 200:
        raise Exception(
            f'Could not get NOID from {settings.NOIDMINTER_URL}: ' \
            f'{r.status_code} {r.reason}'
        )
    return r.json()[0]
