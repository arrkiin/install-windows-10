import bpy
from .bl_utils import MoveItemOperator
from .ed_base import EditorBase, ed
from .addon import prefs
from .layout_helper import lh, draw_pme_layout
from .ui import utitle, tag_redraw
from .operators import (
    WM_OT_pm_select, WM_OT_pme_user_pie_menu_call, PME_OT_panel_hide
)
from .panel_utils import (
    panel,
    add_panel, remove_panel, hidden_panel, get_hidden_panels, bl_panel_types)
from . import pme


def draw_pme_panel(self, context):
    pr = prefs()
    if self.pme_data in pr.pie_menus:
        pm = pr.pie_menus[self.pme_data]
        if issubclass(self.__class__, bpy.types.Header):
            if not self.__class__.poll(context):
                return
            self.layout.separator()
        draw_pme_layout(
            pm, self.layout.column(True),
            WM_OT_pme_user_pie_menu_call._draw_item, None, 1)

    else:
        tp = hidden_panel(self.pme_data) or getattr(
            bpy.types, self.pme_data, None)
        if not tp:
            return
        pme.context.layout = self.layout
        PME_OT_interactive_panels_toggle.enabled = False
        panel(tp, False, False, root=True)
        PME_OT_interactive_panels_toggle.enabled = True


def poll_pme_panel(cls, context):
    pr = prefs()
    if cls.pm_name not in pr.pie_menus:
        return True

    pm = pr.pie_menus[cls.pm_name]
    return pm.poll(cls, context)


class PME_OT_interactive_panels_toggle(bpy.types.Operator):
    bl_idname = "pme.interactive_panels_toggle"
    bl_label = "Toggle Interactive Panels Mode (PME)"
    bl_description = "Toggle interactive panels mode"
    bl_options = {'REGISTER'}

    active = False
    enabled = True

    action = bpy.props.EnumProperty(
        items=(
            ('TOGGLE', "Toggle", ""),
            ('ENABLE', "Enable", ""),
            ('DISABLE', "Disable", ""),
        ),
        options={'SKIP_SAVE'}
    )

    @staticmethod
    def _draw(self, context):
        if not PME_OT_interactive_panels_toggle.enabled:
            return

        pm = prefs().selected_pm
        if not pm:
            return

        lh.lt(self.layout.row(True), 'EXEC_DEFAULT')
        is_pg = pm.mode == 'PANEL' or pm.mode == 'HPANEL' or \
            pm.mode == 'DIALOG'
        lh.operator(
            WM_OT_pm_select.bl_idname,
            "" if is_pg else "Select Item",
            pm.ed.icon if is_pg else 'NONE',
            mode={'PANEL', 'HPANEL', 'DIALOG'})

        tp = self.__class__
        tp_name = tp.bl_idname if hasattr(tp, "bl_idname") else tp.__name__

        if pm.mode == 'HPANEL':
            lh.operator(
                PME_OT_panel_hide.bl_idname, "Hide Panel",
                panel=tp_name)
        elif pm.mode == 'PANEL':
            lh.operator(
                PME_OT_panel_add.bl_idname, "Add to Panel Group",
                panel=tp_name, mode='BLENDER')
        elif pm.mode == 'DIALOG':
            lh.operator(
                PME_OT_panel_add.bl_idname, "Add to Popup Dialog",
                panel=tp_name, mode='DIALOG')

        lh.operator(
            PME_OT_interactive_panels_toggle.bl_idname, "", 'QUIT',
            action='DISABLE')

    def execute(self, context):
        pr = prefs()
        if self.action == 'ENABLE' or self.action == 'TOGGLE' and \
                not pr.interactive_panels:
            pr.interactive_panels = True
        else:
            pr.interactive_panels = False

        # if self.__class__.ahpg and self.hpg:
        #     self.__class__.ahpg = self.hpg
        #     return {'FINISHED'}

        return {'FINISHED'}


class PME_OT_panel_add(bpy.types.Operator):
    bl_idname = "pme.panel_add"
    bl_label = "Add Panel"
    bl_description = "Add panel"
    bl_options = {'INTERNAL'}
    bl_property = "item"

    enum_items = None

    def get_items(self, context):
        if not PME_OT_panel_add.enum_items:
            enum_items = []

            if self.mode == 'BLENDER':
                def _add_item(tp_name, tp):
                    ctx, _, name = tp_name.partition("_PT_")
                    label = hasattr(
                        tp, "bl_label") and tp.bl_label or name or tp_name
                    if name:
                        if name == label or utitle(name) == label:
                            label = "[%s] %s" % (ctx, utitle(label))
                        else:
                            label = "[%s] %s (%s)" % (ctx, label, name)

                    enum_items.append((tp_name, label, ""))

                for tp in bl_panel_types():
                    _add_item(
                        tp.bl_idname if hasattr(tp, "bl_idname") else
                        tp.__name__,
                        tp)

                for tp_name, tp in get_hidden_panels().items():
                    _add_item(tp_name, tp)

            elif self.mode == 'PME':
                for pm in prefs().pie_menus:
                    if pm.mode == 'DIALOG':
                        enum_items.append((pm.name, pm.name, ""))

            PME_OT_panel_add.enum_items = enum_items

        return PME_OT_panel_add.enum_items

    item = bpy.props.EnumProperty(items=get_items, options={'SKIP_SAVE'})
    index = bpy.props.IntProperty(default=-1, options={'SKIP_SAVE'})
    mode = bpy.props.StringProperty(options={'SKIP_SAVE'})
    panel = bpy.props.StringProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        pr = prefs()
        if not self.panel:
            self.panel = self.item

        pm = pr.selected_pm

        if self.mode == 'BLENDER' or self.mode == 'DIALOG':
            tp = hidden_panel(self.panel) or getattr(
                bpy.types, self.panel, None)
            if not tp:
                return {'CANCELLED'}

        if self.mode == 'DIALOG':
            pmi = pm.ed.add_pd_row(pm)
            pmi.mode = 'CUSTOM'
            pmi.text = "panel(T.%s, frame=True, header=True, expand=None)" % \
                self.panel
        else:
            pmi = pm.pmis.add()
            pmi.mode = 'MENU'
            pmi.text = self.panel

        if self.mode == 'BLENDER' or self.mode == 'DIALOG':
            if hasattr(tp, "bl_label") and tp.bl_label:
                pmi.name = tp.bl_label
            else:
                ctx, _, name = self.panel.partition("_PT_")
                pmi.name = utitle(name if name else ctx)

        elif self.mode == 'PME':
            pmi.name = self.panel

        idx = len(pm.pmis) - 1
        if self.index != -1 and self.index != idx:
            pm.pmis.move(idx, self.index)
            idx = self.index

        if self.index != -1:
            pm.update_panel_group()
        else:
            add_panel(
                pm.name, idx, pmi.text, pmi.name, pm.panel_space,
                pm.panel_region, pm.panel_context, pm.panel_category,
                draw_pme_panel, poll_pme_panel)

        if self.mode == 'PME':
            pr.update_tree()

        tag_redraw()
        return {'FINISHED'}

    def _draw(self, menu, context):
        lh.lt(menu.layout, 'INVOKE_DEFAULT')
        lh.operator(
            self.__class__.bl_idname, "Popup Dialog", ed('DIALOG').icon,
            mode='PME', index=self.index)
        lh.operator(
            self.__class__.bl_idname, "Panel", 'BLENDER',
            mode='BLENDER', index=self.index)

        lh.sep()

        lh.prop(prefs(), "interactive_panels")

    def invoke(self, context, event):
        if not self.mode:
            context.window_manager.popup_menu(self._draw)
        elif not self.panel:
            PME_OT_panel_add.enum_items = None
            context.window_manager.invoke_search_popup(self)
        else:
            return self.execute(context)
        return {'FINISHED'}


class PME_OT_panel_item_move(MoveItemOperator, bpy.types.Operator):
    bl_idname = "pme.panel_item_move"

    def get_collection(self):
        return prefs().selected_pm.pmis

    def finish(self):
        prefs().selected_pm.update_panel_group()
        tag_redraw()


class PME_OT_panel_item_remove(bpy.types.Operator):
    bl_idname = "pme.panel_item_remove"
    bl_label = "Remove Panel"
    bl_description = "Remove the panel"
    bl_options = {'INTERNAL'}

    idx = bpy.props.IntProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        pr = prefs()
        pm = pr.selected_pm

        remove_panel(pm.name, self.idx)

        pm.pmis.remove(self.idx)

        pr.update_tree()
        tag_redraw()
        return {'CANCELLED'}


class PME_OT_panel_item_menu(bpy.types.Operator):
    bl_idname = "pme.panel_item_menu"
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
        lh.label(
            text if text.strip() else "Menu",
            ed('DIALOG').icon if pmi.text in pr.pie_menus else 'BLENDER')

        lh.sep(check=True)

        lh.operator(
            PME_OT_panel_add.bl_idname, "Add Panel", 'ZOOMIN',
            index=self.idx)

        if len(pm.pmis) > 1:
            lh.operator(
                PME_OT_panel_item_move.bl_idname,
                "Move Panel", 'ARROW_LEFTRIGHT',
                old_idx=self.idx)

            lh.sep(check=True)

        lh.operator(
            PME_OT_panel_item_remove.bl_idname,
            "Remove", 'X',
            idx=self.idx)

    def execute(self, context):
        context.window_manager.popup_menu(self._draw)
        return {'FINISHED'}


pme.props.StringProperty("pg", "pg_context", "ANY")
pme.props.StringProperty("pg", "pg_category", "My Category")
pme.props.StringProperty("pg", "pg_space", "VIEW_3D")
pme.props.StringProperty("pg", "pg_region", "TOOLS")


class Editor(EditorBase):

    def __init__(self):
        self.id = 'PANEL'
        EditorBase.__init__(self)

        self.docs = "#Panel_Group_Editor"
        self.use_preview = False
        self.sub_item = False
        self.has_hotkey = False
        self.default_pmi_data = "pg?"
        self.supported_slot_modes = {'EMPTY', 'MENU'}

    def draw_keymap(self, layout, data):
        row = layout.row(True)
        row.prop(data, "panel_space", "")
        row.prop(data, "panel_region", "")

        if data.panel_region != 'HEADER':
            row = layout.row(True)
            row.prop(data, "panel_context", "")
            row.prop(data, "panel_category", "", icon='LINENUMBERS_ON')

    def draw_hotkey(self, layout, data):
        pass

    def draw_items(self, layout, pm):
        col = layout.column(True)

        for idx, pmi in enumerate(pm.pmis):
            lh.row(col)

            icon = ed('DIALOG').icon if pmi.text in prefs().pie_menus \
                else 'BLENDER'

            lh.prop(pmi, "label", "", icon)

            lh.operator(
                PME_OT_panel_item_menu.bl_idname,
                "", 'COLLAPSEMENU',
                idx=idx)

        lh.row(col)
        lh.operator(PME_OT_panel_add.bl_idname, "Add Panel")
