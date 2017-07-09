import bpy
from . import operator_utils
from . import selection_state
from .bl_utils import MoveItemOperator
from .ed_base import (
    EditorBase, ed, PME_OT_pmi_copy, PME_OT_pmi_paste, WM_OT_pmi_data_edit,
    PME_OT_pmi_remove)
from .addon import prefs
from .ui import tag_redraw, shorten_str
from .layout_helper import lh
from . import pme


class WM_OT_script_add(bpy.types.Operator):
    bl_idname = "wm.script_add"
    bl_label = "Add Command"
    bl_description = "Add a command"
    bl_options = {'INTERNAL'}

    index = bpy.props.IntProperty()

    def execute(self, context):
        pm = prefs().selected_pm
        pmi = pm.pmis.add()

        idx = 1
        while True:
            name = "Command %d" % idx
            if name not in pm.pmis:
                break
            idx += 1

        pmi.mode = 'COMMAND'
        pmi.name = name

        idx = len(pm.pmis) - 1
        if self.index != -1 and self.index != idx:
            pm.pmis.move(idx, self.index)

        tag_redraw()
        return {'FINISHED'}


class PME_OT_script_item_move(MoveItemOperator, bpy.types.Operator):
    bl_idname = "pme.script_item_move"

    def get_collection(self):
        return prefs().selected_pm.pmis

    def finish(self):
        tag_redraw()


class WM_OT_script_specials_call(bpy.types.Operator):
    bl_idname = "wm.script_specials_call"
    bl_label = ""
    bl_description = "Menu"
    bl_options = {'INTERNAL'}

    pm_item = bpy.props.IntProperty()

    def _draw(self, menu, context):
        pr = prefs()
        pm = pr.selected_pm
        pmi = pm.pmis[self.pm_item]

        lh.lt(menu.layout, operator_context='INVOKE_DEFAULT')
        text, _, _, _, _ = pmi.parse()
        lh.label(shorten_str(text) if text.strip() else "Menu", pm.ed.icon)

        lh.sep(check=True)

        lh.operator(
            WM_OT_pmi_data_edit.bl_idname,
            "Edit Item", 'TEXT',
            idx=self.pm_item,
            ok=False)

        lh.sep(check=True)

        lh.operator(
            PME_OT_pmi_copy.bl_idname, None, 'COPYDOWN',
            pm_item=self.pm_item)

        if pr.pmi_clipboard:
            lh.operator(
                PME_OT_pmi_paste.bl_idname, None, 'PASTEDOWN',
                pm_item=self.pm_item)

        if len(pm.pmis) > 1:
            lh.sep(check=True)

            lh.operator(
                PME_OT_script_item_move.bl_idname,
                "Move Item", 'ARROW_LEFTRIGHT',
                old_idx=self.pm_item)

            lh.sep(check=True)

            lh.operator(
                PME_OT_pmi_remove.bl_idname,
                "Remove", 'X',
                idx=self.pm_item)

    def execute(self, context):
        context.window_manager.popup_menu(self._draw)
        return {'FINISHED'}


pme.props.BoolProperty("s", "s_undo")


class Editor(EditorBase):

    def __init__(self):
        self.id = 'SCRIPT'
        EditorBase.__init__(self)

        self.docs = "#Stack_Key_Editor"
        self.use_slot_icon = False
        self.use_preview = False
        self.default_pmi_data = "s?"
        self.supported_slot_modes = {'EMPTY', 'COMMAND', 'HOTKEY'}

    def draw_extra_settings(self, layout, pm):
        EditorBase.draw_extra_settings(self, layout, pm)
        layout.prop(pm, "s_undo")

    def draw_items(self, layout, pm):
        col = layout.column(True)

        for idx, pmi in enumerate(pm.pmis):
            lh.row(col)

            lh.operator(
                WM_OT_pmi_data_edit.bl_idname, "", ed('SCRIPT').icon,
                idx=idx,
                ok=False)

            lh.prop(pmi, "name", "")

            lh.operator(
                WM_OT_script_specials_call.bl_idname,
                "", 'COLLAPSEMENU',
                pm_item=idx)

        lh.lt(col)
        lh.operator(
            WM_OT_script_add.bl_idname, "Add Command", index=-1)
