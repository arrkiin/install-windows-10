import bpy
import traceback
from . import pme
from .bl_utils import MoveItemOperator, RemoveItemOperator, AddItemOperator
from .ed_base import (
    EditorBase, PME_OT_pmi_copy, PME_OT_pmi_paste, WM_OT_pmi_data_edit)
from .operators import PME_OT_sticky_key
from .addon import prefs
from .ui import tag_redraw, shorten_str
from .macro_utils import update_macro, init_macros
from .layout_helper import lh


class PME_OT_macro_exec_base:
    bl_idname = "pme.macro_exec_base"
    bl_label = "Macro Command"
    bl_options = {'INTERNAL'}

    macro_locals = None

    cmd = bpy.props.StringProperty(
        maxlen=1024, options={'SKIP_SAVE', 'HIDDEN'})

    def execute(self, context):
        try:
            exec(
                self.cmd, pme.context.globals,
                PME_OT_macro_exec_base.macro_locals)
        except:
            traceback.print_exc()
            return {'CANCELLED'}

        ret = {'CANCELLED'} \
            if PME_OT_macro_exec_base.macro_locals.get("stop", False) \
            else {'FINISHED'}
        PME_OT_macro_exec_base.macro_locals.pop("stop", None)
        return ret


class PME_OT_macro_exec1(bpy.types.Operator):
    bl_idname = "pme.macro_exec1"
    bl_label = "Macro Command"
    bl_options = {'INTERNAL'}

    cmd = bpy.props.StringProperty(
        maxlen=1024, options={'SKIP_SAVE', 'HIDDEN'})

    def execute(self, context):
        PME_OT_macro_exec_base.macro_locals = pme.context.gen_locals()

        return PME_OT_macro_exec_base.execute(self, context)


class PME_OT_macro_item_move(MoveItemOperator, bpy.types.Operator):
    bl_idname = "pme.macro_item_move"

    def get_collection(self):
        return prefs().selected_pm.pmis

    def finish(self):
        tag_redraw()
        update_macro(prefs().selected_pm)


class PME_OT_macro_item_remove(RemoveItemOperator, bpy.types.Operator):
    bl_idname = "pme.macro_item_remove"

    def get_collection(self):
        return prefs().selected_pm.pmis

    def finish(self):
        tag_redraw()
        update_macro(prefs().selected_pm)


class PME_OT_macro_item_add(AddItemOperator, bpy.types.Operator):
    bl_idname = "pme.macro_item_add"
    bl_label = "Add Command"
    bl_description = "Add a command"

    def get_collection(self):
        return prefs().selected_pm.pmis

    def finish(self, item):
        collection = self.get_collection()
        idx = 1
        while True:
            name = "Command %d" % idx
            if name not in collection:
                break
            idx += 1

        item.mode = 'COMMAND'
        item.name = name

        tag_redraw()
        update_macro(prefs().selected_pm)


class PME_OT_macro_item_menu(bpy.types.Operator):
    bl_idname = "pme.macro_specials_call"
    bl_label = ""
    bl_description = "Menu"
    bl_options = {'INTERNAL'}

    idx = bpy.props.IntProperty()

    def _draw(self, menu, context):
        pr = prefs()
        pm = pr.selected_pm
        pmi = pm.pmis[self.idx]

        lh.lt(menu.layout, operator_context='INVOKE_DEFAULT')
        text, _, _, _, _ = pmi.parse()
        lh.label(shorten_str(text) if text.strip() else "Menu", pm.ed.icon)

        lh.sep(check=True)

        lh.operator(
            WM_OT_pmi_data_edit.bl_idname,
            "Edit Item", 'TEXT',
            idx=self.idx,
            ok=False)

        lh.operator(
            PME_OT_macro_item_add.bl_idname, "Add Command", 'ZOOMIN',
            idx=self.idx)

        lh.sep(check=True)

        lh.operator(
            PME_OT_pmi_copy.bl_idname, None, 'COPYDOWN',
            pm_item=self.idx)

        if pr.pmi_clipboard:
            lh.operator(
                PME_OT_pmi_paste.bl_idname, None, 'PASTEDOWN',
                pm_item=self.idx)

        if len(pm.pmis) > 1:
            lh.sep(check=True)

            lh.operator(
                PME_OT_macro_item_move.bl_idname,
                "Move Item", 'ARROW_LEFTRIGHT',
                old_idx=self.idx)

            lh.sep(check=True)

            lh.operator(
                PME_OT_macro_item_remove.bl_idname,
                "Remove", 'X',
                idx=self.idx)

    def execute(self, context):
        context.window_manager.popup_menu(self._draw)
        return {'FINISHED'}


class Editor(EditorBase):

    def __init__(self):
        self.id = 'MACRO'
        EditorBase.__init__(self)

        self.docs = "#Macro_Operator_Editor"
        self.use_slot_icon = False
        self.use_preview = False
        self.default_pmi_data = "m?"
        self.supported_slot_modes = {'EMPTY', 'COMMAND', 'MENU'}
        self.supported_sub_menus = {'STICKY', 'MACRO'}

    def draw_items(self, layout, pm):
        pr = prefs()

        col = layout.column(True)

        for idx, pmi in enumerate(pm.pmis):
            lh.row(col)

            icon = self.icon
            if pmi.icon:
                icon = pmi.icon
            elif pmi.text in pr.pie_menus:
                icon = pr.pie_menus[pmi.text].ed.icon

            lh.operator(
                WM_OT_pmi_data_edit.bl_idname, "", icon,
                idx=idx,
                ok=False)

            lh.prop(pmi, "name", "")

            lh.operator(
                PME_OT_macro_item_menu.bl_idname,
                "", 'COLLAPSEMENU',
                idx=idx)

        lh.lt(col)
        lh.operator(PME_OT_macro_item_add.bl_idname, "Add Command")


def register():
    init_macros(PME_OT_macro_exec1, PME_OT_macro_exec_base, PME_OT_sticky_key)