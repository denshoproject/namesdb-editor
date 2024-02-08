from http import HTTPStatus

from django.conf import settings
import httpx


def get_noids(num_ids=1):
    r = httpx.post(
        settings.NOIDMINTER_URL,
        data={'num': num_ids},
        auth=(settings.NOIDMINTER_USERNAME, settings.NOIDMINTER_PASSWORD),
        follow_redirects=True,
    )
    if r.status_code != HTTPStatus.OK:
        raise Exception(
            f'Could not get NOID from {settings.NOIDMINTER_URL}: {r}'
        )
    return r.json()
