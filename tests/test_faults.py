import pytest
import requests
import responses
from django.core.mail import EmailMessage

from getresponse.mail import GetResponseBackend


@pytest.fixture
def backend(settings):
    settings.GETRESPONSE_API_TOKEN = 'test-token'
    settings.GETRESPONSE_ADDRESSES = {
        'webmaster@localhost': 'gr-id-1',
    }
    return GetResponseBackend()


@pytest.fixture
def email_message():
    return EmailMessage(
        subject='Test subject',
        body='Test body',
        to=['john.doe@example.com'],
    )


@responses.activate
def test_read_timeout(backend, email_message):
    responses.add(
        responses.POST,
        'https://api.getresponse.com/v3/transactional-emails',
        body=requests.exceptions.ReadTimeout(),
    )
    n = backend.send_messages([email_message])
    assert n == 0
