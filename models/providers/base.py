from odoo import models


class WAProviderBase(models.AbstractModel):
    _name = 'wa.provider.base'
    _description = 'WhatsApp Provider Base (Strategy)'
    """
    Base strategy interface for WhatsApp providers.

    Notes about NotImplementedError:
    - This AbstractModel defines the contract. Each concrete provider must
      override the methods below. The default implementation raises
      NotImplementedError to signal "abstract" methods.
    - If a method is not overridden by a provider, calling it will raise
      NotImplementedError at runtime, making missing implementations explicit.
    """

    # Inbound (webhook)
    def normalize_inbound(self, account, raw, request=None):
        """
        Normalize the inbound webhook payload.
        Should return:
          - a dict with standardized keys, or
          - a list[dict] when the provider sends batches.
        """
        raise NotImplementedError

    def inbound_handle(self, account, raw, request=None):
        """
        Optional hook to process normalized inbound payloads and create messages
        or channels as needed. Should return a dict with results or status.
        Concrete providers may override; base raises NotImplementedError to
        indicate the app expects providers to implement when used.
        """
        raise NotImplementedError

    # Outbound (sending)
    def send_text(self, account, mobile, message):
        """Send a text message. Return a dict with ok, id, status_code, raw."""
        raise NotImplementedError

    def send_media(self, account, mobile, *, caption='', b64=None, mime=None, filename=None):
        """Send a media message with caption. Return a dict with ok, id, status_code, raw."""
        raise NotImplementedError

    # Instance lifecycle
    def create_instance(self, account):
        """Create the provider instance. Return a dict with ok, status_code, etc."""
        raise NotImplementedError

    def delete_instance(self, account):
        """Delete the provider instance. Return a dict with ok, status_code, etc."""
        raise NotImplementedError

    def check_status(self, account):
        """Check instance connection/state. Return a dict with ok, state, status_code."""
        raise NotImplementedError

    def connect(self, account):
        """Start/connect instance and, if applicable, return qrcode_b64. Return a dict with ok, qrcode_b64, status_code."""
        raise NotImplementedError

    def restart(self, account):
        """Restart the provider instance. Return a dict with ok, status_code, etc."""
        raise NotImplementedError

    def disconnect(self, account):
        """Logout/disconnect the instance. Return a dict with ok, status_code, etc."""
        raise NotImplementedError

    def get_profile_image(self, account, remote_jid=None):
        """Return profile image as base64 or False if not available."""
        return False