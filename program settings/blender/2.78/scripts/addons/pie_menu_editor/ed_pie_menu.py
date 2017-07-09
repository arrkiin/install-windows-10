import bpy
from .ed_base import (
    EditorBase, PME_OT_pmi_copy, PME_OT_pmi_paste,
    WM_OT_pmi_data_edit, WM_OT_pmi_icon_select)
from .addon import prefs
from .layout_helper import lh
from .constants import ARROW_ICONS
from .ui import tag_redraw, shorten_str
from . import pme


class WM_OT_pmi_move(bpy.types.Operator):
    bl_idname = "wm.pmi_move"
    bl_label = ""
    bl_description = "Move an item"
    bl_options = {'INTERNAL'}

    pm_item = bpy.props.IntProperty()
    idx = bpy.props.IntProperty()

    def _draw(self, menu, context):
        pm = prefs().selected_pm

        lh.lt(menu.layout)

        idx = 0
        for pmi in pm.pmis:
            name = pmi.name

            if pmi.mode == 'EMPTY':
                name = ". . ."

            lh.operator(
                WM_OT_pmi_move.bl_idname, name, ARROW_ICONS[idx],
                pm_item=self.pm_item,
                idx=idx)

            idx += 1

    def execute(self, context):
        pm = prefs().selected_pm

        if self.idx == -1:
            bpy.context.window_manager.popup_menu(
                self._draw,
                title="Move '%s' item" % pm.pmis[self.pm_item].name)
        elif self.idx != self.pm_item:
            pm.pmis.move(self.pm_item, self.idx)
            idx2 = \
                self.idx - 1 if self.pm_item < self.idx else self.idx + 1
            if idx2 != self.pm_item:
                pm.pmis.move(idx2, self.pm_item)

            tag_redraw()

        return {'FINISHED'}


class PME_OT_pm_item_clear(bpy.types.Operator):
    bl_idname = "pme.pmi_clear"
    bl_label = "Clear"
    bl_description = "Clear the item"
    bl_options = {'INTERNAL'}

    idx = bpy.props.IntProperty()

    def execute(self, context):
        pr = prefs()
        pm = pr.selected_pm
        pmi = pm.pmis[self.idx]

        pmi.text = ""
        pmi.name = ""
        pmi.icon = ""
        pmi.mode = 'EMPTY'

        pr.update_tree()
        tag_redraw()
        return {'CANCELLED'}


class WM_OT_pmi_specials_call(bpy.types.Operator):
    bl_idname = "wm.pmi_specials_call"
    bl_label = ""
    bl_description = "Menu"
    bl_options = {'INTERNAL'}

    pm_item = bpy.props.IntProperty()

    def _draw(self, menu, context):
        pr = prefs()
        pm = pr.selected_pm
        pmi = pm.pmis[self.pm_item]

        lh.lt(menu.layout, operator_context='INVOKE_DEFAULT')
        text, icon, _, _, _ = pmi.parse()
        lh.label(shorten_str(text) if text.strip() else "Menu", icon)

        lh.sep(check=True)

        lh.operator(
            WM_OT_pmi_data_edit.bl_idname,
            "Edit Item", 'TEXT',
            idx=self.pm_item,
            ok=False)

        lh.sep(check=True)

        if pmi.mode != 'EMPTY':
            lh.operator(
                PME_OT_pmi_copy.bl_idname, None, 'COPYDOWN',
                pm_item=self.pm_item)

        if pr.pmi_clipboard:
            lh.operator(
                PME_OT_pmi_paste.bl_idname, None, 'PASTEDOWN',
                pm_item=self.pm_item)

        lh.sep(check=True)

        lh.operator(
            WM_OT_pmi_move.bl_idname, "Move Item", 'ARROW_LEFTRIGHT',
            pm_item=self.pm_item,
            idx=-1)

        lh.sep(check=True)

        lh.operator(
            PME_OT_pm_item_clear.bl_idname,
            "Clear", 'X',
            idx=self.pm_item)

    def execute(self, context):
        context.window_manager.popup_menu(self._draw)
        return {'FINISHED'}


pme.props.IntProperty("pm", "pm_radius", -1)
pme.props.IntProperty("pm", "pm_confirm", -1)
pme.props.IntProperty("pm", "pm_threshold", -1)
pme.props.BoolProperty("pm", "pm_flick", True)


class Editor(EditorBase):

    def __init__(self):
        self.id = 'PMENU'
        EditorBase.__init__(self)

        self.docs = "#Pie_Menu_Editor"
        self.default_pmi_data = "pm?"
        self.supported_open_modes = {'PRESS', 'HOLD', 'DOUBLE_CLICK'}

    def draw_extra_settings(self, layout, pm):
        EditorBase.draw_extra_settings(self, layout, pm)
        subcol = layout.column(True)
        subcol.prop(pm, "pm_radius", "Radius", icon='MAN_ROT')
        if pm.pm_flick:
            subcol.prop(pm, "pm_threshold", "Threshold", icon='MAN_ROT')
            subcol.prop(pm, "pm_confirm", "Confirm Threshold", icon='MAN_ROT')
        layout.prop(pm, "pm_flick")

    def draw_items(self, layout, pm):
        column = layout.column(True)

        for idx in range(0, 8):
            pmi = pm.pmis[idx]
            lh.row(column)

            lh.operator(
                WM_OT_pmi_data_edit.bl_idname, "", ARROW_ICONS[idx],
                idx=idx,
                ok=False)

            icon = pmi.parse_icon('FILE_HIDDEN')

            lh.operator(
                WM_OT_pmi_icon_select.bl_idname, "", icon,
                idx=idx,
                icon="")

            lh.prop(pmi, "name", "")

            lh.operator(
                WM_OT_pmi_specials_call.bl_idname,
                "", 'COLLAPSEMENU',
                pm_item=idx)
