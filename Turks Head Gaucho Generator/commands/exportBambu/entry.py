"""Export for Bambu: one STL per jig body, all in the same coordinates.

Drag the jig + cord outline files into Bambu Studio together and answer
Yes to "load as a single object with multiple parts". Parts keep their
positions, so each can get its own filament without splitting.
"""

import os
import re
import struct
import tempfile

import adsk.core
import adsk.fusion

from ... import config
from ...lib import fusionAddInUtils as futil
from ...lib.turksHead import builder

app = adsk.core.Application.get()
ui = app.userInterface

CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_exportBambu'
CMD_NAME = "Export Turk's Head Jig for Bambu"
CMD_DESCRIPTION = ("Write one STL per body (jig, cord outlines, lid) in shared "
                   "coordinates, ready to load as one multi-part object.")
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
    panel = ui.workspaces.itemById(config.WORKSPACE_ID).toolbarPanels.itemById(config.PANEL_ID)
    control = panel.controls.itemById(CMD_ID) or panel.controls.addCommand(cmd_def)
    control.isPromoted = IS_PROMOTED


def stop():
    panel = ui.workspaces.itemById(config.WORKSPACE_ID).toolbarPanels.itemById(config.PANEL_ID)
    control = panel.controls.itemById(CMD_ID)
    if control:
        control.deleteMe()
    cmd_def = ui.commandDefinitions.itemById(CMD_ID)
    if cmd_def:
        cmd_def.deleteMe()


def command_created(args: adsk.core.CommandCreatedEventArgs):
    cmd = args.command
    cmd.isRepeatable = False
    inputs = cmd.commandInputs
    sel = inputs.addSelectionInput('target', 'Jig', "Select a Turk's head jig")
    sel.addSelectionFilter('Occurrences')
    sel.setSelectionLimits(1, 1)
    occ = builder.preselected_jig()
    if occ:
        sel.addSelection(occ)
    inputs.addDropDownCommandInput(
        'quality', 'Mesh quality',
        adsk.core.DropDownStyles.TextListDropDownStyle)
    q = inputs.itemById('quality').listItems
    q.add('Medium', False)
    q.add('High', True)
    inputs.addBoolValueInput('lid', 'Include lid (separate file)', True, '', True)
    futil.add_handler(cmd.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(cmd.select, command_select, local_handlers=local_handlers)
    futil.add_handler(cmd.destroy, command_destroy, local_handlers=local_handlers)


def _safe(s):
    return re.sub(r'[^\w\- ]+', '', s).strip()


def _bodies(occ, want_lid):
    """Visible solid bodies of the jig (incl. sub-components), in assembly context."""
    out = []
    comps = [(occ, occ.component)]
    for sub in occ.childOccurrences:
        comps.append((sub, sub.component))
    for o, comp in comps:
        for b in comp.bRepBodies:
            if not b.isSolid or 'tool' in b.name.lower():
                continue
            if not b.isLightBulbOn:
                continue
            if b.name == 'Lid' and not want_lid:
                continue
            out.append(b.createForAssemblyContext(o) if o else b)
    return out


def command_execute(args: adsk.core.CommandEventArgs):
    inputs = args.command.commandInputs
    sel = inputs.itemById('target')
    occ = builder.jig_occurrence(sel.selection(0).entity) if sel.selectionCount else None
    if not occ:
        ui.messageBox("Select a Turk's head jig.")
        return
    dlg = ui.createFolderDialog()
    dlg.title = 'Folder for STL files'
    if dlg.showDialog() != adsk.core.DialogResults.DialogOK:
        return
    folder = dlg.folder
    base = _safe(occ.component.name)
    high = inputs.itemById('quality').selectedItem.name == 'High'
    em = adsk.fusion.Design.cast(app.activeProduct).exportManager

    groups = {}
    for b in _bodies(occ, inputs.itemById('lid').value):
        groups.setdefault(re.sub(r' \(\d+\)$', '', b.name), []).append(b)

    refine = (adsk.fusion.MeshRefinementSettings.MeshRefinementHigh if high
              else adsk.fusion.MeshRefinementSettings.MeshRefinementMedium)
    written, failed = [], []
    tmp = tempfile.mkdtemp()
    for name, bodies in groups.items():
        path = os.path.join(folder, '{} - {}.stl'.format(base, _safe(name)))
        parts = []
        for i, b in enumerate(bodies):
            part = os.path.join(tmp, '{}_{}.stl'.format(_safe(name), i))
            try:
                opt = em.createSTLExportOptions(b, part)
                opt.isBinaryFormat = True
                opt.meshRefinement = refine
                em.execute(opt)
                parts.append(part)
            except Exception as e:
                failed.append('{} #{}: {}'.format(name, i + 1, e))
        if parts:
            _merge_stl(parts, path)
            written.append('{} ({} bod{})'.format(os.path.basename(path), len(parts),
                                                  'y' if len(parts) == 1 else 'ies'))

    msg = 'Wrote to {}:\n  {}'.format(folder, '\n  '.join(written))
    if failed:
        msg += '\n\nFailed:\n  ' + '\n  '.join(failed)
    msg += ('\n\nBambu Studio: select the Jig and Cord outline files, drag them in '
            'together, answer Yes to "load as a single object with multiple parts". '
            'Load the Lid file on its own.')
    ui.messageBox(msg, CMD_NAME)


def _merge_stl(srcs, dst):
    """Concatenate binary STL files into one."""
    tris, count = [], 0
    for f in srcs:
        with open(f, 'rb') as fh:
            data = fh.read()
        n = struct.unpack_from('<I', data, 80)[0]
        tris.append(data[84:84 + 50 * n])
        count += n
    with open(dst, 'wb') as fh:
        fh.write(b'Turks head jig export'.ljust(80, b' '))
        fh.write(struct.pack('<I', count))
        for t in tris:
            fh.write(t)


def command_select(args: adsk.core.SelectionEventArgs):
    if args.activeInput.id == 'target':
        args.isSelectable = builder.jig_occurrence(args.selection.entity) is not None


def command_destroy(args: adsk.core.CommandEventArgs):
    global local_handlers
    local_handlers = []
