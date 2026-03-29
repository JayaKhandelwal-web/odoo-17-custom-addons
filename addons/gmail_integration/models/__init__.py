# -*- coding: utf-8 -*-
from . import gmail_config          # FIRST - provides configuration for all other models
from . import gmail_account         # SECOND - depends on gmail_config for OAuth methods
from . import gmail_message
from . import gmail_attachment
from . import gmail_template
from . import gmail_mass_mail
from . import gmail_send_mail
from . import gmail_sync_log
from . import gmail_sync_service
from . import gmail_thread
from . import gmail_mail_interceptor
from . import gmail_dashboard
from . import gmail_alert_handler    # newly Added - FIRST
from . import gmail_alert_settings   # newly Added - SECOND (depends on handler)
