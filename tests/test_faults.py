import logging

import pytest
import requests
import responses
from django.core.mail import EmailMessage

from getresponse.mail import GetResponseBackend, GetResponseSendError

ENDPOINT = 'https://api.getresponse.com/v3/transactional-emails'

# What GetResponse answers a request it will not act on: an error document naming
# the problem, where the status code alone only says which kind of problem it is.
ERROR_DOCUMENT = {
    'code': 1019,
    'codeDescription': 'The server is currently unable to handle the request due to a maintenance',
    'httpStatus': 503,
    'message': 'Transactional email service is experiencing temporary issues',
}


@pytest.fixture
def settings_with_sender(settings):
    settings.GETRESPONSE_API_TOKEN = 'test-token'
    settings.GETRESPONSE_ADDRESSES = {
        'webmaster@localhost': 'gr-id-1',
    }
    return settings


@pytest.fixture
def backend(settings_with_sender):
    return GetResponseBackend()


@pytest.fixture
def silent_backend(settings_with_sender):
    return GetResponseBackend(fail_silently=True)


@pytest.fixture
def email_message():
    return EmailMessage(
        subject='Test subject',
        body='Test body',
        to=['john.doe@example.com'],
    )


@responses.activate
def test_a_delivered_message_reports_the_id_it_was_given(backend, email_message):
    responses.add(responses.POST, ENDPOINT, json={'transactionalEmailId': 'gr-msg-1'}, status=201)

    result = backend.send_messages([email_message])

    assert result == 1
    assert result.getresponse_ids == ['gr-msg-1']


@responses.activate
def test_a_transport_failure_reaches_the_caller(backend, email_message):
    responses.add(responses.POST, ENDPOINT, body=requests.exceptions.ReadTimeout('no answer'))

    with pytest.raises(GetResponseSendError) as refusal:
        backend.send_messages([email_message])

    # No response came back, so the exception raised on the way out is the whole
    # of what there is to say about why.
    assert 'no answer' in str(refusal.value)
    assert isinstance(refusal.value.__cause__, requests.exceptions.ReadTimeout)


@responses.activate
def test_a_rejected_request_reaches_the_caller_with_what_the_api_said(backend, email_message):
    responses.add(responses.POST, ENDPOINT, json=ERROR_DOCUMENT, status=503)

    with pytest.raises(GetResponseSendError) as refusal:
        backend.send_messages([email_message])

    # The error document rather than the status line: "1019, under maintenance" is
    # what tells a caller whether asking again could work.
    assert '1019' in str(refusal.value)
    assert isinstance(refusal.value.__cause__, requests.HTTPError)
    # A caller handling mail generically catches `OSError`, which is what both
    # `smtplib.SMTPException` and the wrapped `requests` failure already are.
    assert isinstance(refusal.value, OSError)


@responses.activate
def test_a_success_that_creates_nothing_reaches_the_caller(backend, email_message):
    """A 2xx that is not a 201 carries no id, so nothing was queued for delivery.

    The send count cannot say so on its own — it comes back one short either way —
    which is why this path reports a reason like any other refusal.
    """
    responses.add(responses.POST, ENDPOINT, json={}, status=202)

    with pytest.raises(GetResponseSendError, match='202'):
        backend.send_messages([email_message])


@responses.activate
def test_a_silenced_refusal_is_logged_rather_than_lost(silent_backend, email_message, caplog):
    responses.add(responses.POST, ENDPOINT, json=ERROR_DOCUMENT, status=503)

    with caplog.at_level(logging.ERROR):
        result = silent_backend.send_messages([email_message])

    assert result == 0
    record, = caplog.records
    assert '1019' in record.getMessage()
    # What varies is an argument, so the message itself is the same for every refusal.
    assert '1019' not in record.msg
    assert record.exc_info is not None


@responses.activate
def test_a_silenced_transport_failure_is_logged_rather_than_lost(silent_backend, email_message, caplog):
    responses.add(responses.POST, ENDPOINT, body=requests.exceptions.ReadTimeout('no answer'))

    with caplog.at_level(logging.ERROR):
        result = silent_backend.send_messages([email_message])

    assert result == 0
    assert 'no answer' in caplog.records[0].getMessage()
