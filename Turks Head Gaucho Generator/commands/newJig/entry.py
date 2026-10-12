"""Turk's Head Jig: build a new jig."""

import os

import adsk.core

from ... import config
from ...lib import fusionAddInUtils as futil
from ...lib.turksHead import builder, dialog

app = adsk.core.Application.get()
ui = app.userInterface

CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_newJig'
CMD_NAME = "Turk's Head Gaucho Jig"
CMD_DESCRIPTION = ("Generate a Turk's head or two-colour gaucho fan jig: cord lanes sized "
                   "to your cord, with over/under marked for each colour.")
IS_PROMOTED = False

ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', '')

local_handlers = []


def start():
    cmd_def = ui.commandDefinitions.itemById(CMD_ID)
    if cmd_def:
        cmd_def.deleteMe()
    cmd_def = ui.commandDefinitions.addButtonDefinition(
        CMD_ID, CMD_NAME, CMD_DESCRIPTION, ICON_FOLDER)
    futil.add_handler(cmd_def.commandCreated, command_created)

    workspace = ui.workspaces.itemById(config.WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(config.PANEL_ID)
    control = panel.controls.itemById(CMD_ID) or panel.controls.addCommand(cmd_def)
    control.isPromoted = IS_PROMOTED


def stop():
    workspace = ui.workspaces.itemById(config.WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(config.PANEL_ID)
    control = panel.controls.itemById(CMD_ID)
    if control:
        control.deleteMe()
    cmd_def = ui.commandDefinitions.itemById(CMD_ID)
    if cmd_def:
        cmd_def.deleteMe()


def command_created(args: adsk.core.CommandCreatedEventArgs):
    futil.log(f'{CMD_NAME} Command Created Event')
    cmd = args.command
    cmd.isRepeatable = False
    cmd.setDialogInitialSize(360, 420)
    inputs = cmd.commandInputs
    dialog.add_inputs(inputs)
    dialog.refresh(inputs)

    futil.add_handler(cmd.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(cmd.inputChanged, command_input_changed, local_handlers=local_handlers)
    futil.add_handler(cmd.validateInputs, command_validate_input, local_handlers=local_handlers)
    futil.add_handler(cmd.destroy, command_destroy, local_handlers=local_handlers)


def command_execute(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME} Command Execute Event')
    p = dialog.read_inputs(args.command.commandInputs)
    report(p, builder.run_build(p))


def command_input_changed(args: adsk.core.InputChangedEventArgs):
    dialog.refresh(args.inputs.command.commandInputs, args.input.id)


def command_validate_input(args: adsk.core.ValidateInputsEventArgs):
    args.areInputsValid = not dialog.problems(
        dialog.read_inputs(args.inputs.command.commandInputs))


def command_destroy(args: adsk.core.CommandEventArgs):
    global local_handlers
    local_handlers = []
    futil.log(f'{CMD_NAME} Command Destroy Event')


def report(p, problems):
    """Non-fatal problems: always logged; shown only with the dialog's debug box ticked."""
    for msg in problems:
        futil.log(msg, adsk.core.LogLevels.WarningLogLevel)
    if p.get('debug') and problems:
        msg = '\n\n'.join(problems[:5])
        if len(problems) > 5:
            msg += f'\n\n…and {len(problems) - 5} more.'
        ui.messageBox(f'{len(problems)} non-fatal problem(s):\n\n{msg}',
                      f'{CMD_NAME} — debug')
