# __init__.py (Root Level) - Fixed Hooks Version
from . import models
from . import wizards

# Import fixed hooks for automatic Employee ID generation
from .hooks import post_init_hook, uninstall_hook
