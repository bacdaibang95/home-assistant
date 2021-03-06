"""
Support for the Mailgun mail service.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/notify.mailgun/
"""
import logging

import voluptuous as vol

from homeassistant.components.notify import (
    PLATFORM_SCHEMA, BaseNotificationService,
    ATTR_TITLE, ATTR_TITLE_DEFAULT, ATTR_DATA)
from homeassistant.const import (CONF_TOKEN, CONF_DOMAIN,
                                 CONF_RECIPIENT, CONF_SENDER)
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)
REQUIREMENTS = ['https://github.com/pschmitt/pymailgun/'
                'archive/1.3.zip#'
                'pymailgun==1.3']

# Images to attach to notification
ATTR_IMAGES = 'images'

# Configuration item for the domain to use.
CONF_SANDBOX = 'sandbox'

# Default sender name
DEFAULT_SENDER = 'hass@{domain}'
# Default sandbox value
DEFAULT_SANDBOX = False

# pylint: disable=no-value-for-parameter
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_TOKEN): cv.string,
    vol.Required(CONF_RECIPIENT): vol.Email(),
    vol.Optional(CONF_DOMAIN): cv.string,
    vol.Optional(CONF_SENDER): vol.Email(),
    vol.Optional(CONF_SANDBOX, default=DEFAULT_SANDBOX): cv.boolean,
})


def get_service(hass, config, discovery_info=None):
    """Get the Mailgun notification service."""
    mailgun_service = MailgunNotificationService(config.get(CONF_DOMAIN),
                                                 config.get(CONF_SANDBOX),
                                                 config.get(CONF_TOKEN),
                                                 config.get(CONF_SENDER),
                                                 config.get(CONF_RECIPIENT))
    if mailgun_service.connection_is_valid():
        return mailgun_service
    else:
        return None


class MailgunNotificationService(BaseNotificationService):
    """Implement a notification service for the Mailgun mail service."""

    def __init__(self, domain, sandbox, token, sender, recipient):
        """Initialize the service."""
        self._client = None  # Mailgun API client
        self._domain = domain
        self._sandbox = sandbox
        self._token = token
        self._sender = sender
        self._recipient = recipient

    def initialize_client(self):
        """Initialize the connection to Mailgun."""
        from pymailgun import Client
        self._client = Client(self._token, self._domain, self._sandbox)
        _LOGGER.debug('Mailgun domain: %s', self._client.domain)
        self._domain = self._client.domain
        if not self._sender:
            self._sender = DEFAULT_SENDER.format(domain=self._domain)

    def connection_is_valid(self):
        """Check whether the provided credentials are valid."""
        from pymailgun import (MailgunCredentialsError, MailgunDomainError)
        try:
            self.initialize_client()
        except MailgunCredentialsError:
            _LOGGER.exception('Invalid credentials')
            return False
        except MailgunDomainError as mailgun_error:
            _LOGGER.exception(mailgun_error)
            return False
        return True

    def send_message(self, message="", **kwargs):
        """Send a mail to the recipient."""
        from pymailgun import MailgunError
        subject = kwargs.get(ATTR_TITLE, ATTR_TITLE_DEFAULT)
        data = kwargs.get(ATTR_DATA)
        files = data.get(ATTR_IMAGES) if data else None

        try:
            # Initialize the client in case it was not.
            if self._client is None:
                self.initialize_client()
            resp = self._client.send_mail(sender=self._sender,
                                          to=self._recipient,
                                          subject=subject,
                                          text=message,
                                          files=files)
            _LOGGER.debug('Message sent: %s', resp)
        except MailgunError as mailgun_error:
            _LOGGER.exception('Failed to send message: %s', mailgun_error)
