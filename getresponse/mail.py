import base64
from email.mime.base import MIMEBase
import threading
from urllib.parse import urljoin
import logging

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
import requests


logger = logging.getLogger(__name__)


class GetResponseBackend(BaseEmailBackend):
    def __init__(self, **kwargs):
        self._session = None
        self._endpoint = getattr(settings, 'GETRESPONSE_ENDPOINT', 'https://api.getresponse.com/v3/')
        self._lock = threading.RLock()

    def send_messages(self, msgs):
        count = 0
        with self._lock, self:  # self is used to obtain connection
            for msg in msgs:
                if self._send_message(msg):
                    count += 1
        return count

    def _send_message(self, msg):
        payload = self.message_to_payload(msg)
        url = urljoin(self._endpoint, 'transactional-emails')
        response = self._session.post(url, json=payload)
        try:
            response.raise_for_status()
        except requests.RequestException:
            logger.exception("getresponse api call failed")
            return False
        return response.status_code == 201

    def message_to_payload(self, msg):
        if len(msg.to) != 1:
            raise ValueError("Exactly one msg.to address is required.")
        payload = {
            'fromField': {
                # msg.from_email is ignored.
                'fromFieldId': settings.GETRESPONSE_FROM_FIELD_ID,
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
        if tag_id := getattr(msg, 'tag_id', None):
            payload['tag'] = {
                'tagId': tag_id,
            }
        return payload

    def attachments_to_payload(self, attachments):
        return [self.attachment_to_payload(attachment) for attachment in attachments]

    def attachment_to_payload(self, attachment):
        if isinstance(attachment, MIMEBase):
            raise ValueError('MIMEBase attachments are currently not supported by GetResponse backend.')

        filename, content, mimetype = attachment
        return {
            'fileName': filename,
            'mimeType': mimetype,
            'content': base64.b64encode(content if isinstance(content, bytes) else content.encode('utf-8')),
        }

    def open(self):
        if self._session:
            self.close()

        self._session = requests.Session()
        self._session.headers['X-Auth-Token'] = f'api-key {settings.GETRESPONSE_API_TOKEN}'

    def close(self):
        self._session.close()
        self._session = None
