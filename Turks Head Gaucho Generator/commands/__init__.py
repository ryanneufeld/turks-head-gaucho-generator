# Each command module has start() and stop(). Add new commands here.

from .newJig import entry as newJig
from .editJig import entry as editJig
from .exportBambu import entry as exportBambu

commands = [newJig, editJig, exportBambu]


def start():
    for command in commands:
        command.start()


def stop():
    for command in commands:
        command.stop()
