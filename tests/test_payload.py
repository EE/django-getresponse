import pytest
from django.core.mail import EmailMessage

from getresponse.mail import GetResponseBackend


@pytest.fixture
def backend(settings):
    settings.GETRESPONSE_ADDRESSES = {
        'webmaster@localhost': 'gr-id-1',
        'replies@example.com': 'gr-id-2',
    }
    return GetResponseBackend()


def message(**kwargs):
    return EmailMessage(
        subject='Test subject',
        body='Test body',
        to=['john.doe@example.com'],
        **kwargs,
    )


def test_reply_to_travels_as_the_from_field_registered_for_it(backend):
    payload = backend.message_to_payload(message(reply_to=['replies@example.com']))

    assert payload['replyTo'] == {'fromFieldId': 'gr-id-2'}


def test_a_message_without_a_reply_to_sends_none(backend):
    assert 'replyTo' not in backend.message_to_payload(message())


def test_an_unregistered_reply_to_is_refused(backend):
    with pytest.raises(ValueError):
        backend.message_to_payload(message(reply_to=['nobody@example.com']))


def test_more_than_one_reply_to_is_refused(backend):
    with pytest.raises(ValueError):
        backend.message_to_payload(message(reply_to=['replies@example.com', 'webmaster@localhost']))
