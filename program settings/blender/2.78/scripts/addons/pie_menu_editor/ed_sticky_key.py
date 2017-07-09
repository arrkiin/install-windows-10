import bpy
from traceback import print_exc
from . import keymap_helper
from . import pme
from .ed_base import (
    EditorBase, PME_OT_pmi_copy, PME_OT_pmi_paste, WM_OT_pmi_data_edit)
from .addon import prefs
from .ui import tag_redraw, shorten_str
from .operator_utils import find_statement
from .layout_helper import lh


class WM_OT_sticky_specials_call(bpy.types.Operator):
    bl_idname = "wm.sticky_specials_call"
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

    def execute(self, context):
        context.window_manager.popup_menu(self._draw)
        return {'FINISHED'}


class PME_OT_sticky_key_edit(bpy.types.Operator):
    bl_idname = "pme.sticky_key_edit"
    bl_label = "Save and Restore Previous Value"
    bl_description = "Save and restore the previous value"
    bl_options = {'INTERNAL'}

    pmi_prop = None
    pmi_value = None

    @staticmethod
    def parse_prop_value(text):
        prop, value = find_statement(text)
        if not prop:
            PME_OT_sticky_key_edit.pmi_prop = None
            PME_OT_sticky_key_edit.pmi_value = None
        else:
            PME_OT_sticky_key_edit.pmi_prop = prop
            PME_OT_sticky_key_edit.pmi_value = value

    def execute(self, context):
        cl = self.__class__
        pr = prefs()
        pm = pr.selected_pm
        pm.pmis[1].mode = 'COMMAND'
        pm.pmis[1].text = cl.pmi_prop + " = value"
        pm.pmis[0].mode = 'COMMAND'
        pm.pmis[0].text = "value = %s; %s = %s" % (
            cl.pmi_prop, cl.pmi_prop, cl.pmi_value)

        pr.pmi_data.info("")
        pr.leave_mode()
        tag_redraw()

        return {'FINISHED'}


class Editor(EditorBase):

    def __init__(self):
        self.id = 'STICKY'
        EditorBase.__init__(self)

        self.docs = "#Sticky_Key_Editor"
        self.use_slot_icon = False
        self.use_preview = False
        self.sub_item = False
        self.default_pmi_data = "sk?"
        self.supported_slot_modes = {'EMPTY', 'COMMAND', 'HOTKEY'}

    def draw_items(self, layout, pm):
        col = layout.column(True)

        for idx, pmi in enumerate(pm.pmis):
            lh.row(col)

            lh.operator(
                WM_OT_pmi_data_edit.bl_idname, "",
                'MESH_CIRCLE' if idx == 0 else 'SOLID',
                idx=idx,
                ok=False)

            lh.prop(pmi, "name", "")

            lh.operator(
                WM_OT_sticky_specials_call.bl_idname,
                "", 'COLLAPSEMENU',
                pm_item=idx)
