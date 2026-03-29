from odoo import api, SUPERUSER_ID

def set_default_action(cr, registry):
    """Set the dashboard as the default action when opening the module."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    try:
        # Get the module menu
        menu = env.ref('transport_logbook.menu_transport_logbook_root', raise_if_not_found=False)
        if not menu:
            return
            
        # Set the vehicle dashboard as the default action
        dashboard_action = env.ref('transport_logbook.action_transport_vehicle_dashboard', raise_if_not_found=False)
        if dashboard_action:
            menu.action = dashboard_action.id
    except Exception as e:
        # Log the error but don't crash
        import logging
        _logger = logging.getLogger(__name__)
        _logger.error("Error in post_init_hook: %s", e)
