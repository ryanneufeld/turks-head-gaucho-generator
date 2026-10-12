"""Edit Turk's Head Jig: change an existing jig's settings and rebuild it in place."""

import os

import adsk.core

from ... import config
from ...lib import fusionAddInUtils as futil
from ...lib.turksHead import builder, dialog
from ..newJig.entry import report

app = adsk.core.Application.get()
ui = app.userInterface

CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_editJig'
CMD_NAME = "Edit Turk's Head Gaucho Jig"
CMD_DESCRIPTION = ("Change the settings of an existing Turk's head jig and rebuild it. "
                   "Position is kept.")
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
    cmd.setDialogInitialSize(360, 460)
    inputs = cmd.commandInputs

    sel = inputs.addSelectionInput('target', 'Jig to edit', "Select a Turk's head jig")
    sel.addSelectionFilter('Occurrences')
    sel.setSelectionLimits(1, 1)
    dialog.add_inputs(inputs)

    occ = builder.preselected_jig()
    if occ:
        sel.addSelection(occ)
        dialog.load_inputs(inputs, builder.jig_params(occ))
    dialog.refresh(inputs)

    futil.add_handler(cmd.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(cmd.inputChanged, command_input_changed, local_handlers=local_handlers)
    futil.add_handler(cmd.validateInputs, command_validate_input, local_handlers=local_handlers)
    futil.add_handler(cmd.select, command_select, local_handlers=local_handlers)
    futil.add_handler(cmd.destroy, command_destroy, local_handlers=local_handlers)


def command_execute(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME} Command Execute Event')
    inputs = args.command.commandInputs
    p = dialog.read_inputs(inputs)
    report(p, builder.run_build(p, edit_occ=dialog.target_occ(inputs)))


def command_input_changed(args: adsk.core.InputChangedEventArgs):
    inputs = args.inputs.command.commandInputs
    if args.input.id == 'target':
        occ = dialog.target_occ(inputs)
        if occ:
            dialog.load_inputs(inputs, builder.jig_params(occ))
    dialog.refresh(inputs, args.input.id)


def command_validate_input(args: adsk.core.ValidateInputsEventArgs):
    inputs = args.inputs.command.commandInputs
    args.areInputsValid = (dialog.target_occ(inputs) is not None
                           and not dialog.problems(dialog.read_inputs(inputs)))


def command_select(args: adsk.core.SelectionEventArgs):
    """Only jig occurrences can be picked."""
    if args.activeInput.id == 'target':
        args.isSelectable = builder.jig_occurrence(args.selection.entity) is not None


def command_destroy(args: adsk.core.CommandEventArgs):
    global local_handlers
    local_handlers = []
    futil.log(f'{CMD_NAME} Command Destroy Event')
