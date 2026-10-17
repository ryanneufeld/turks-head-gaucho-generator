# Turk's Head Gaucho Generator — Fusion add-in entry point.
# Adds "Turk's Head Gaucho Jig" and "Edit Turk's Head Gaucho Jig" to Solid > Create.

import sys

# Fusion keeps an add-in's submodules cached between Stop and Run, so edits
# to lib/ or commands/ would be ignored until Fusion restarts. Drop them here
# so every Run loads the current files.
for _m in [m for m in list(sys.modules) if m.startswith(__name__ + '.')]:
    del sys.modules[_m]

from . import commands
from .lib import fusionAddInUtils as futil


def run(context):
    try:
        commands.start()
    except Exception:  # pylint: disable=broad-exception-caught
        futil.handle_error('run')


def stop(context):
    try:
        futil.clear_handlers()
        commands.stop()
    except Exception:  # pylint: disable=broad-exception-caught
        futil.handle_error('stop')
