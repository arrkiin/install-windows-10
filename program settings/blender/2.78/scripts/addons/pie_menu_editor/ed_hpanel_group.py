import bpy
from .ed_base import EditorBase
from .addon import prefs, temp_prefs
from .layout_helper import lh
from .panel_utils import (
    hide_panel, unhide_panel, bl_panel_types, is_panel_hidden)
from .constants import SPACE_ITEMS, REGION_ITEMS
from .ui import tag_redraw
from .operators import *


class PME_OT_hpanel_menu(bpy.types.Operator):
    bl_idname = "pme.panel_hide_menu"
    bl_label = "Hide Panels"
    bl_description = "Hide panels"

    def _draw(self, menu, context):
        lh.lt(menu.layout, 'INVOKE_DEFAULT')
        lh.operator(PME_OT_panel_hide.bl_idname, None, 'ZOOMIN')
        lh.operator(PME_OT_panel_hide_by.bl_idname, None, 'ZOOMIN')
        lh.sep()

        lh.prop(prefs(), "interactive_panels")

    def execute(self, context):
        context.window_manager.popup_menu(self._draw, self.bl_description)
        return {'FINISHED'}


class PME_OT_hpanel_remove(bpy.types.Operator):
    bl_idname = "pme.hpanel_remove"
    bl_label = "Unhide Panel"
    bl_description = "Unhide panel"
    bl_options = {'INTERNAL'}

    idx = bpy.props.IntProperty()

    def execute(self, context):
        pm = prefs().selected_pm

        if self.idx == -1:
            for pmi in pm.pmis:
                unhide_panel(pmi.text)

            pm.pmis.clear()

        else:
            pmi = pm.pmis[self.idx]
            unhide_panel(pmi.text)
            pm.pmis.remove(self.idx)

        tag_redraw()
        return {'FINISHED'}


class Editor(EditorBase):

    def __init__(self):
        self.id = 'HPANEL'
        EditorBase.__init__(self)

        self.docs = "#Hiding_Unused_Panels"
        self.use_preview = False
        self.sub_item = False
        self.has_hotkey = False
        self.has_extra_settings = False
        self.default_pmi_data = "hpg?"
        self.supported_slot_modes = {'EMPTY'}

    def draw_keymap(self, layout, data):
        pass

    def draw_hotkey(self, layout, data):
        pass

    def draw_items(self, layout, pm):
        tpr = temp_prefs()

        row = layout.row()
        row.template_list(
            "WM_UL_panel_list", "",
            pm, "pmis", tpr, "hidden_panels_idx", rows=10)

        lh.column(row)
        lh.operator(PME_OT_hpanel_menu.bl_idname, "", 'ZOOMIN')

        if len(pm.pmis):
            lh.operator(
                PME_OT_hpanel_remove.bl_idname, "", 'ZOOMOUT',
                idx=tpr.hidden_panels_idx)
            lh.operator(
                PME_OT_hpanel_remove.bl_idname, "", 'X', idx=-1)

        lh.sep()

        lh.layout.prop(prefs(), "panel_info_visibility", "", expand=True)
