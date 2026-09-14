import base64
import json
import logging
import threading
from email.mime.base import MIMEBase
from pprint import pformat
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


# One wording for a refusal however it is reported, and a `%s` so that the reason can be
# logged as an argument rather than formatted into the message it is reported under.
_REFUSAL = 'GetResponse refused a message: %s'


class GetResponseSendError(OSError):
    """GetResponse did not accept a message for delivery.

    An `OSError` because that is what a caller handling mail generically already
    catches: `smtplib.SMTPException`, which Django's own SMTP backend raises, and
    `requests.RequestException`, which this wraps, are both subclasses of it.
    """

    def __init__(self, reason):
        super().__init__(_REFUSAL % reason)
        self.reason = reason


def _failure_reason(exc):
    """What GetResponse said, or what stopped it being asked.

    A rejected request answers with the API's own error document, which names the
    problem where the status line only numbers it; a transport failure has no response.
    """
    if exc.response is None:
        return str(exc)
    try:
        return pformat(exc.response.json())
    except json.decoder.JSONDecodeError:
        return exc.response.content


class GetResponseSendResult(int):
    def __new__(cls, value, getresponse_ids):
        return super().__new__(cls, value)

    def __init__(self, value, getresponse_ids):
        self.getresponse_ids = getresponse_ids


class GetResponseBackend(BaseEmailBackend):
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self._session = None
        self._endpoint = getattr(settings, 'GETRESPONSE_ENDPOINT', 'https://api.getresponse.com/v3/')
        self._lock = threading.RLock()

    def send_messages(self, msgs):
        transactional_email_ids = []
        count = 0

        with self._lock, self:  # self is used to obtain connection
            for msg in msgs:
                try:
                    transactional_email_id = self._send_message(msg)
                except GetResponseSendError as e:
                    if not self.fail_silently:
                        raise
                    # Silenced for the caller, so the log is where the reason still goes.
                    logger.exception(_REFUSAL, e.reason)
                    transactional_email_id = None

                if transactional_email_id:
                    count += 1

                transactional_email_ids.append(transactional_email_id)
        return GetResponseSendResult(count, getresponse_ids=transactional_email_ids)

    def _send_message(self, msg):
        payload = self.message_to_payload(msg)
        url = urljoin(self._endpoint, 'transactional-emails')
        timeout = getattr(settings, 'GETRESPONSE_TIMEOUT', 10)
        try:
            response = self._session.post(url, json=payload, timeout=timeout)
            response.raise_for_status()
        except requests.RequestException as e:
            raise GetResponseSendError(_failure_reason(e)) from e
        if response.status_code != 201:
            # The id lives in the body of a 201; any other success code means the API
            # accepted the request without creating a message.
            raise GetResponseSendError(f'the API answered {response.status_code} instead of creating the message')
        return response.json()["transactionalEmailId"]

    def message_to_payload(self, msg):
        if len(msg.to) != 1:
            raise ValueError("Exactly one msg.to address is required.")
        payload = {
            'fromField': {
                'fromFieldId': self.get_sender(msg.from_email),
            },
            'subject': msg.subject,
            'content': {
                'plain': msg.body,
            },
            'recipients': {
                'to': {'email': msg.to[0]},
                'cc': msg.cc,
                'bcc': msg.bcc,
            },
            'attachments': self.attachments_to_payload(msg.attachments),
        }

        if isinstance(msg, EmailMultiAlternatives):
            for alternative_content, mimetype in msg.alternatives:
                if mimetype == 'text/html' and 'html' not in payload['content']:
                    payload['content']['html'] = alternative_content
                else:
                    raise ValueError("Only single text/html alternative is supported by GetResponse backend.")

        if tag_id := getattr(msg, 'tag_id', None):
            payload['tag'] = {
                'tagId': tag_id,
            }
        return payload

    def get_sender(self, from_email):
        # if msg.from_email is listed in users settings with FieldId as value, use this address
        if not settings.GETRESPONSE_ADDRESSES.get(from_email):
            raise ValueError(f"Given from_email ({from_email}) is not present in GETRESPONSE_ADDRESSES.")
        return settings.GETRESPONSE_ADDRESSES.get(from_email)

    def attachments_to_payload(self, attachments):
        return [self.attachment_to_payload(attachment) for attachment in attachments]

    def attachment_to_payload(self, attachment):
        if isinstance(attachment, MIMEBase):
            raise ValueError('MIMEBase attachments are currently not supported by GetResponse backend.')

        filename, content, mimetype = attachment
        return {
            'fileName': filename,
            'mimeType': mimetype,
            'content': base64.b64encode(
                content if isinstance(content, bytes)
                else content.encode('utf-8')
            ).decode(),
        }

    def open(self):
        if self._session:
            self.close()

        self._session = requests.Session()
        self._session.headers['X-Auth-Token'] = f'api-key {settings.GETRESPONSE_API_TOKEN}'

    def close(self):
        self._session.close()
        self._session = None
