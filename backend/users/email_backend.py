import logging

from django.conf import settings
from django.core.mail.backends.smtp import EmailBackend

logger = logging.getLogger(__name__)

class ConfigurableEmailBackend(EmailBackend):
    """
    Custom email backend that pulls configuration from the database.
    Falls back to settings.py configuration if no active database config exists.
    """
    def __init__(self, **kwargs):
        from .models import EmailConfiguration
        
        # Get active configuration from database
        try:
            config = EmailConfiguration.objects.filter(is_active=True).first()
            if config:
                logger.info(f"Using email configuration: {config.name}")
                kwargs.setdefault('host', config.email_host)
                kwargs.setdefault('port', config.email_port)
                kwargs.setdefault('username', config.email_host_user)
                kwargs.setdefault('password', config.email_host_password)
                kwargs.setdefault('use_tls', config.email_use_tls)
                # Set default from email as a global setting if not provided in the email
                settings.DEFAULT_FROM_EMAIL = config.default_from_email
            else:
                logger.warning("No active email configuration found, using settings.py defaults")
        except Exception as e:
            logger.error(f"Error loading email configuration: {str(e)}")
            # Handle case where the table might not exist yet (during migrations)
            pass

        super().__init__(**kwargs)