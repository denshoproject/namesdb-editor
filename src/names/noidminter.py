import requests
from http import HTTPStatus

from django.conf import settings


def get_noids(num_ids=1):
    r = requests.post(
        settings.NOIDMINTER_URL,
        data={'num': num_ids},
        auth=(settings.NOIDMINTER_USERNAME, settings.NOIDMINTER_PASSWORD)
    )
    if r.status_code != HTTPStatus.OK:
        raise Exception(
            f'Could not get NOID from {settings.NOIDMINTER_URL}: ' \
            f'{r.status_code} {r.reason}'
        )
    return r.json()
