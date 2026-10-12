import os
import traceback

import adsk.core

app = adsk.core.Application.get()
ui = app.userInterface

# Read DEBUG from the add-in's config.py without a package-relative import.
try:
    from ... import config
    DEBUG = config.DEBUG
    ADDIN_NAME = os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
except Exception:
    DEBUG = False
    ADDIN_NAME = 'Add-in'


def log(message: str, level: adsk.core.LogLevels = adsk.core.LogLevels.InfoLogLevel,
        force_console: bool = False):
    """Write to the Fusion log file; also the Text Commands window when DEBUG."""
    print(message)
    if level == adsk.core.LogLevels.ErrorLogLevel:
        app.log(message, level, adsk.core.LogTypes.FileLogType)
    if DEBUG or force_console:
        app.log(message, level, adsk.core.LogTypes.ConsoleLogType)


def handle_error(name: str, show_message_box: bool = False):
    """Log the current exception; optionally show it in a message box."""
    log('===== Error =====', adsk.core.LogLevels.ErrorLogLevel)
    log(f'{name}\n{traceback.format_exc()}', adsk.core.LogLevels.ErrorLogLevel)
    if show_message_box:
        ui.messageBox(f'{ADDIN_NAME} — {name}\n\n{traceback.format_exc()}')
