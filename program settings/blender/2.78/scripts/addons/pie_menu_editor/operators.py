import bpy
from bpy.props import (
    BoolProperty,
    IntProperty,
    FloatProperty,
    FloatVectorProperty,
    StringProperty,
    EnumProperty,
    CollectionProperty,
    PointerProperty
)
import os
import traceback
from .addon import prefs, temp_prefs, ADDON_PATH
from .bl_utils import bl_context, pbool, pint, pstring, penum
from .layout_helper import lh, draw_pme_layout
from .overlay import Timer
from .ui import tag_redraw, utitle
from .panel_utils import hide_panel, is_panel_hidden, bl_panel_types
from .constants import I_DEBUG, SPACE_ITEMS, REGION_ITEMS, PM_ITEMS_M
from .debug_utils import *
from .macro_utils import execute_macro
from . import (
    pme,
    selection_state,
    operator_utils,
    keymap_helper
)
from .keymap_helper import MOUSE_BUTTONS, is_key_pressed, StackKey


def popup_dialog_pie(event, draw, title=""):
    pr = prefs()
    pr.pie_menu_prefs.save()
    bpy.context.user_preferences.view.pie_menu_radius = 0
    bpy.context.window_manager.popup_menu_pie(event, draw, title)
    pr.pie_menu_prefs.restore()


class WM_OT_pme_none(bpy.types.Operator):
    bl_idname = "wm.pme_none"
    bl_label = ""
    bl_options = {'INTERNAL'}

    def execute(self, context):
        return {'FINISHED'}


class WM_OT_pm_select(bpy.types.Operator):
    bl_idname = "wm.pm_select"
    bl_label = "Select Menu"
    bl_description = "Select a menu to edit"

    pm_name = pstring()
    use_mode_icons = pbool()
    mode = penum(
        items=PM_ITEMS_M,
        default=set(),
        options={'SKIP_SAVE', 'ENUM_FLAG'})

    def _draw(self, menu, context):
        lh.lt(menu.layout, 'INVOKE_DEFAULT')

        lh.menu("PME_MT_pm_new", "New", 'ZOOMIN')
        lh.operator(
            PME_OT_pm_search_and_select.bl_idname, None, 'VIEWZOOM',
            mode=self.mode)

        pr = prefs()
        if len(pr.pie_menus) == 0:
            return

        lh.sep()
        apm = pr.selected_pm

        keys = sorted(pr.pie_menus.keys())
        for k in keys:
            pm = pr.pie_menus[k]
            if self.mode and pm.mode not in self.mode:
                continue

            if self.use_mode_icons:
                icon = pm.ed.icon

            else:
                icon = 'SPACE3'
                if pm == apm:
                    icon = 'SPACE2'

            lh.operator(
                WM_OT_pm_select.bl_idname, k, icon,
                pm_name=k)

    def execute(self, context):
        if not self.pm_name:
            bpy.context.window_manager.popup_menu(
                self._draw, title=self.bl_label)
        else:
            pr = prefs()
            tpr = temp_prefs()
            pm = None
            idx = pr.pie_menus.find(self.pm_name)
            if idx >= 0:
                pr.active_pie_menu_idx = idx
                pm = pr.pie_menus[idx]

            if pr.tree_mode:
                for idx, link in enumerate(tpr.links):
                    if link.pm_name == self.pm_name and not link.path:
                        tpr.links_idx = idx
                        break

                if pm:
                    pr.tree.expand_km(pm.km_name)

        tag_redraw()
        return {'CANCELLED'}


class PME_OT_pm_search_and_select(bpy.types.Operator):
    bl_idname = "pme.pm_search_and_select"
    bl_label = "Search and Select"
    bl_options = {'INTERNAL'}
    bl_property = "item"

    enum_items = None

    def get_items(self, context):
        pr = prefs()

        if not PME_OT_pm_search_and_select.enum_items:
            enum_items = []

            for k in sorted(pr.pie_menus.keys()):
                pm = pr.pie_menus[k]
                if self.mode and pm.mode not in self.mode:
                    continue
                enum_items.append((pm.name, pm.name, ""))

            PME_OT_pm_search_and_select.enum_items = enum_items

        return PME_OT_pm_search_and_select.enum_items

    item = EnumProperty(items=get_items)
    mode = EnumProperty(
        items=PM_ITEMS_M,
        default=set(),
        options={'SKIP_SAVE', 'ENUM_FLAG'})

    def execute(self, context):
        bpy.ops.wm.pm_select(pm_name=self.item)
        PME_OT_pm_search_and_select.enum_items = None
        return {'FINISHED'}

    def invoke(self, context, event):
        PME_OT_pm_search_and_select.enum_items = None
        context.window_manager.invoke_search_popup(self)
        return {'FINISHED'}


class WM_OT_pme_user_command_exec(bpy.types.Operator):
    bl_idname = "wm.pme_user_command_exec"
    bl_label = ""
    bl_options = {'INTERNAL'}

    cmds = []

    cmd = StringProperty(maxlen=1024, options={'SKIP_SAVE', 'HIDDEN'})

    def execute(self, context):
        pme.context.exec_operator = self
        try:
            exec(self.cmd, pme.context.globals, pme.context.gen_locals())
        except:
            traceback.print_exc()

        pme.context.exec_operator = None
        return {'FINISHED'}


class PME_OT_exec(bpy.types.Operator):
    bl_idname = "pme.exec"
    bl_label = ""
    bl_options = {'INTERNAL'}

    cmds = []

    cmd = StringProperty(maxlen=1024, options={'SKIP_SAVE', 'HIDDEN'})

    def execute(self, context):
        pme.context.exec_operator = self
        try:
            exec(self.cmd, pme.context.globals, pme.context.gen_locals())
        except:
            traceback.print_exc()

        pme.context.exec_operator = None
        return {'FINISHED'}


class PME_OT_panel_hide(bpy.types.Operator):
    bl_idname = "pme.panel_hide"
    bl_label = "Hide Panel"
    bl_description = "Hide panel"
    bl_options = {'INTERNAL'}
    bl_property = "item"

    enum_items = None

    def get_items(self, context):
        if not PME_OT_panel_hide.enum_items:
            enum_items = []
            panel_tp = bpy.types.Panel
            for tp_name in dir(bpy.types):
                tp = getattr(bpy.types, tp_name)
                if tp == panel_tp or not issubclass(tp, panel_tp) or \
                        hasattr(tp, "pme_data") or \
                        tp.bl_space_type == 'USER_PREFERENCES':
                    continue

                label = tp.bl_label if hasattr(tp, "bl_label") else ""
                if not label:
                    label = tp_name

                if hasattr(tp, "bl_idname"):
                    tp_name = tp.bl_idname

                enum_items.append((
                    tp_name,
                    "%s (%s)" % (label, tp_name),
                    ""))

            PME_OT_panel_hide.enum_items = enum_items

        return PME_OT_panel_hide.enum_items

    item = bpy.props.EnumProperty(items=get_items, options={'SKIP_SAVE'})
    panel = bpy.props.StringProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        if not self.panel:
            self.panel = self.item

        # pm = prefs.pie_menus[self.hpg] if self.hpg else \
        pm = prefs().selected_pm
        tp = getattr(bpy.types, self.panel)

        for pmi in pm.pmis:
            if pmi.text == self.panel:
                return {'CANCELLED'}

        pmi = pm.pmis.add()
        pmi.mode = 'MENU'
        pmi.name = tp.bl_label if hasattr(tp, "bl_label") else self.panel
        pmi.text = self.panel

        hide_panel(self.panel)

        tag_redraw()
        return {'FINISHED'}

    def invoke(self, context, event):
        if not self.panel:
            PME_OT_panel_hide.enum_items = None
            context.window_manager.invoke_search_popup(self)
        else:
            return self.execute(context)
        return {'FINISHED'}


class PME_OT_panel_hide_by(bpy.types.Operator):
    bl_idname = "pme.panel_hide_by"
    bl_label = "Hide Panels by ..."
    bl_description = "Hide panels by ..."
    bl_options = {'INTERNAL'}

    space_items = None
    region_items = None
    ctx_items = None
    cat_items = None

    def _get_space_items(self, context):
        if not PME_OT_panel_hide_by.space_items:
            enum_items = [("ANY", "Any Space", "", 'LAYER_ACTIVE', 0)]

            for i, item in enumerate(SPACE_ITEMS):
                enum_items.append((item[0], item[1], "", item[3], i + 1))

            PME_OT_panel_hide_by.space_items = enum_items

        return PME_OT_panel_hide_by.space_items

    def _get_region_items(self, context):
        if not PME_OT_panel_hide_by.region_items:
            enum_items = [("ANY", "Any Region", "", 'LAYER_ACTIVE', 0)]

            for i, item in enumerate(REGION_ITEMS):
                enum_items.append((item[0], item[1], "", item[3], i + 1))

            PME_OT_panel_hide_by.region_items = enum_items

        return PME_OT_panel_hide_by.region_items

    def _get_context_items(self, context):
        if not PME_OT_panel_hide_by.ctx_items:
            enum_items = [("ANY", "Any Context", "", 'LAYER_ACTIVE', 0)]

            contexts = set()
            for tp in bl_panel_types():
                if hasattr(tp, "bl_context"):
                    contexts.add(tp.bl_context)

            for i, c in enumerate(sorted(contexts)):
                enum_items.append((c, c, "", 'LAYER_USED', i + 1))

            PME_OT_panel_hide_by.ctx_items = enum_items

        return PME_OT_panel_hide_by.ctx_items

    def _get_category_items(self, context):
        if not PME_OT_panel_hide_by.cat_items:
            enum_items = [("ANY", "Any Category", "", 'LAYER_ACTIVE', 0)]

            categories = set()
            for tp in bl_panel_types():
                if hasattr(tp, "bl_category"):
                    categories.add(tp.bl_category)

            for i, c in enumerate(sorted(categories)):
                enum_items.append((c, c, "", 'LAYER_USED', i + 1))

            PME_OT_panel_hide_by.cat_items = enum_items

        return PME_OT_panel_hide_by.cat_items

    space = bpy.props.EnumProperty(
        items=_get_space_items,
        name="Space",
        description="Space",
        options={'SKIP_SAVE'})
    region = bpy.props.EnumProperty(
        items=_get_region_items,
        name="Region",
        description="Region",
        options={'SKIP_SAVE'})
    context = bpy.props.EnumProperty(
        items=_get_context_items,
        name="Context",
        description="Context",
        options={'SKIP_SAVE'})
    category = bpy.props.EnumProperty(
        items=_get_category_items,
        name="Category",
        description="Category",
        options={'SKIP_SAVE'})
    mask = bpy.props.StringProperty(
        name="Mask",
        description="Mask",
        options={'SKIP_SAVE'})

    def _filtered_panels(self, num=False):
        if num:
            num_panels = 0
        else:
            panels = []

        for tp in self.panel_types:
            if (
                    tp.bl_space_type != 'USER_PREFERENCES' and
                    (self.space == 'ANY' or
                        tp.bl_space_type == self.space) and
                    (self.region == 'ANY' or
                        tp.bl_region_type == self.region) and
                    (self.context == 'ANY' or hasattr(tp, "bl_context") and
                        tp.bl_context == self.context) and
                    (self.category == 'ANY' or hasattr(tp, "bl_category") and
                        tp.bl_category == self.category) and
                    (not self.mask or hasattr(tp, "bl_label") and
                        self.mask.lower() in tp.bl_label.lower())):
                if is_panel_hidden(tp.__name__):
                    continue

                if num:
                    num_panels += 1
                else:
                    panels.append(tp)

        return num_panels if num else panels

    def check(self, context):
        return True

    def draw(self, context):
        col = self.layout.column(True)
        lh.row(col)
        lh.prop(self, "space", "")
        lh.prop(self, "region", "")
        lh.row(col)
        lh.prop(self, "context", "")
        lh.prop(self, "category", "")
        lh.lt(col)
        lh.prop(self, "mask", "", 'FILTER')
        lh.sep()
        lh.row(col)
        lh.layout.alignment = 'CENTER'
        lh.label("%d panel(s) will be hidden" % self._filtered_panels(True))

    def execute(self, context):
        pm = prefs().selected_pm

        for tp in self._filtered_panels():
            tp_name = tp.__name__
            if hasattr(tp, "bl_idname"):
                tp_name = tp.bl_idname

            pmi = pm.pmis.add()
            pmi.mode = 'MENU'
            pmi.name = tp.bl_label if hasattr(tp, "bl_label") else tp.__name__
            pmi.text = tp_name

            hide_panel(tp_name)

        tag_redraw()
        return {'FINISHED'}

    def invoke(self, context, event):
        PME_OT_panel_hide_by.space_items = None
        PME_OT_panel_hide_by.region_items = None
        PME_OT_panel_hide_by.ctx_items = None
        PME_OT_panel_hide_by.cat_items = None
        self.panel_types = bl_panel_types()
        return context.window_manager.invoke_props_dialog(self)


class PME_OT_sticky_key(bpy.types.Operator):
    bl_idname = "pme.sticky_key"
    bl_label = "Sticky Key (PME)"

    exec_locals = {}
    root_instance = None
    active_instance = None
    idx = 0

    # key = bpy.props.StringProperty(options={'SKIP_SAVE'})
    # on_press = bpy.props.StringProperty(maxlen=1024, options={'SKIP_SAVE'})
    # on_release = bpy.props.StringProperty(maxlen=1024, options={'SKIP_SAVE'})
    pm_name = bpy.props.StringProperty(
        name="Menu Name", maxlen=1024, options={'SKIP_SAVE', 'HIDDEN'})

    @property
    def is_root_instance(self):
        return self == self.root_instance

    def add_timer(self, step=0):
        if self.timer:
            bpy.context.window_manager.event_timer_remove(self.timer)
        self.timer = bpy.context.window_manager.event_timer_add(
            step, bpy.context.window)

    def remove_timer(self):
        if self.timer:
            bpy.context.window_manager.event_timer_remove(self.timer)
            self.timer = None

    def stop(self, cancel=False):
        DBG_STICKY and logw("Stop %d" % self.idx)
        self.result = {'CANCELLED'} if cancel else {'FINISHED'}
        self.add_timer()

    def restart(self):
        DBG_STICKY and logw("Restart %d" % self.idx)
        self.restart_flag = True
        self.add_timer()

    def modal(self, context, event):
        if event.type == 'TIMER' and self.timer:
            # if not self.is_pressed and self.timer.time_duration > 0.2:
            #     if self.root_instance:
            #         self.root_instance.stop()
            #     self.stop()
            #     return {'PASS_THROUGH'}

            if self.result:
                self.remove_timer()

                if self.is_root_instance:
                    PME_OT_sticky_key.root_instance = None
                    self.execute_pmi(1)

                self.root_instance = None

                # if PME_OT_sticky_key.active_instance == self:
                #     PME_OT_sticky_key.active_instance = None
                PME_OT_sticky_key.idx -= 1
                return {'FINISHED'}

            elif self.restart_flag:
                self.remove_timer()
                bpy.ops.pme.sticky_key('INVOKE_DEFAULT')
                self.restart_flag = False

                if self.is_root_instance:
                    return {'PASS_THROUGH'}

                PME_OT_sticky_key.idx -= 1
                return {'FINISHED'}

            return {'PASS_THROUGH'}

        if event.type == 'WINDOW_DEACTIVATE':
            self.stop(cancel=True)

        if not PME_OT_sticky_key.root_instance:
            DBG_STICKY and loge("BUG")
            return {'PASS_THROUGH'}

        if self.restart_flag:
            return {'PASS_THROUGH'}

        elif event.type == 'MOUSEMOVE' or \
                event.type == 'INBETWEEN_MOUSEMOVE':
            return {'PASS_THROUGH'}

        if event.type == self.root_instance.key:
            if event.value == 'RELEASE':
                if self.root_instance:
                    self.root_instance.stop()
                self.stop()

            elif event.value == 'PRESS':
                self.is_pressed = True
                if self.root_instance and self.timer:
                    self.remove_timer()

            return {'PASS_THROUGH'}

        if event.value != 'ANY' and event.value != 'NOTHING':
            self.restart()
            return {'PASS_THROUGH'}

        return {'PASS_THROUGH'}

    def execute_pmi(self, idx):
        try:
            pm = prefs().pie_menus[self.root_instance.pm_name]
            pmi = pm.pmis[idx]
            if pmi.mode == 'HOTKEY':
                keymap_helper.run_operator_by_hotkey(bpy.context, pmi.text)
            elif pmi.mode == 'COMMAND':
                if idx == 0:
                    PME_OT_sticky_key.exec_locals = pme.context.gen_locals()
                pme.context.exec_locals = PME_OT_sticky_key.exec_locals
                exec(
                    operator_utils.add_default_args(pmi.text),
                    pme.context.globals,
                    PME_OT_sticky_key.exec_locals)
        except:
            traceback.print_exc()

    def invoke(self, context, event):
        if not PME_OT_sticky_key.root_instance:
            if event.value != 'PRESS':
                return {'CANCELLED'}

            PME_OT_sticky_key.root_instance = self
            self.key = event.type
        else:
            if not PME_OT_sticky_key.root_instance.restart_flag and \
                    event.value == 'PRESS' and \
                    event.type == PME_OT_sticky_key.root_instance.key:
                return {'PASS_THROUGH'}

        self.restart_flag = False
        self.result = None
        self.timer = None
        self.is_pressed = True
        self.idx = PME_OT_sticky_key.idx
        PME_OT_sticky_key.idx += 1

        DBG_STICKY and logh("Sticky Key %d" % self.idx)

        self.root_instance = PME_OT_sticky_key.root_instance

        if self.is_root_instance:
            self.execute_pmi(0)
        else:
            # self.is_pressed = False
            self.add_timer(0.02)

        # if not self.root_instance:
        #     if PME_OT_sticky_key.active_instance:
        #         return {'CANCELLED'}
        #     else:
        #         PME_OT_sticky_key.active_instance = self

        # if not self.key:
        #     if event.value == 'RELEASE':
        #         return {'FINISHED'}
        #     self.key = event.type

        context.window_manager.modal_handler_add(self)

        return {'RUNNING_MODAL'}


class PME_OT_timeout(bpy.types.Operator):
    bl_idname = "pme.timeout"
    bl_label = ""
    bl_options = {'INTERNAL'}

    cmd = StringProperty(maxlen=1024, options={'SKIP_SAVE', 'HIDDEN'})
    delay = FloatProperty(default=0.0001, options={'SKIP_SAVE', 'HIDDEN'})

    def modal(self, context, event):
        if event.type == 'TIMER':
            if self.cancelled:
                context.window_manager.event_timer_remove(self.timer)
                self.timer = None
                return {'CANCELLED'}

            if self.timer.time_duration > self.delay:
                self.cancelled = True
                WM_OT_pme_user_command_exec.execute(self, context)
        return {'PASS_THROUGH'}

    def execute(self, context):
        return {'CANCELLED'}

    def invoke(self, context, event):
        self.cancelled = False
        context.window_manager.modal_handler_add(self)
        self.timer = context.window_manager.event_timer_add(
            self.delay, context.window)
        return {'RUNNING_MODAL'}


class PME_OT_restore_mouse_pos(bpy.types.Operator):
    bl_idname = "pme.restore_mouse_pos"
    bl_label = ""
    bl_options = {'INTERNAL'}

    inst = None

    key = pstring()
    x = pint()
    y = pint()
    mode = pint(options={'SKIP_SAVE'})

    def modal(self, context, event):
        # prop = pp.parse(pme.context.pm.data)
        # if not prop.pm_flick:
        #     context.window.cursor_warp(self.x, self.y)

        if event.type == 'WINDOW_DEACTIVATE':
            self.stop()
            return {'PASS_THROUGH'}

        if event.type == 'TIMER':
            if self.cancelled:
                if self.__class__.inst == self:
                    self.__class__.inst = None
                context.window_manager.event_timer_remove(self.timer)
                return {'CANCELLED'}

            if self.mode == 0:
                bpy.ops.pme.restore_mouse_pos(
                    'INVOKE_DEFAULT', key=self.key, x=self.x, y=self.y, mode=1)
                context.window_manager.event_timer_remove(self.timer)
                return {'CANCELLED'}

        if self.mode == 1:
            if event.value == 'RELEASE':
                if event.type == self.key:
                    context.window.cursor_warp(self.x, self.y)
                    self.stop()
                    return {'PASS_THROUGH'}

            elif event.value == 'PRESS':
                if event.type == 'ESC' or event.type == 'RIGHTMOUSE':
                    self.stop()
                    return {'PASS_THROUGH'}

        # if not prop.pm_flick:
        #     return {'RUNNING_MODAL'}

        return {'PASS_THROUGH'}

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        inst = self.__class__.inst
        if inst:
            inst.stop()

        self.cancelled = False
        self.__class__.inst = self

        context.window_manager.modal_handler_add(self)
        time_step = 0.0001 if self.mode == 0 else 0.05
        self.timer = context.window_manager.event_timer_add(
            time_step, context.window)
        return {'RUNNING_MODAL'}

    def stop(self):
        self.cancelled = True


class WM_OT_pme_user_pie_menu_call(bpy.types.Operator):
    bl_idname = "wm.pme_user_pie_menu_call"
    bl_label = "Call Menu (PME)"
    bl_options = {'INTERNAL'}

    hold_inst = None
    active_ops = {}
    pressed_key = None

    pie_menu_name = pstring()
    invoke_mode = pstring()
    keymap = pstring(options={'HIDDEN', 'SKIP_SAVE'})

    @staticmethod
    def _draw_item(pr, pm, pmi, idx):
        hidden = pmi.extract_flags()[2]
        pme.context.pm = pm
        pme.context.pmi = pmi
        pme.context.idx = idx

        if hidden:
            text, icon, _, _, _ = pmi.parse()
            lh.operator(
                WM_OT_pme_none.bl_idname,
                text, icon, emboss=False)

        elif pmi.mode == 'COMMAND':
            op_bl_idname, args, pos_args = \
                operator_utils.find_operator(pmi.text)

            if op_bl_idname and not pos_args:
                # for i, arg in enumerate(args):
                #     args[i] = "p.%s;" % arg
                # args = "".join(args)

                # p = None
                text, icon, _, _, _ = pmi.parse()
                try:
                    exec("str(bpy.ops.%s.idname)" % op_bl_idname)
                    p = lh.operator(op_bl_idname, text, icon)
                    operator_utils.apply_properties(p, args)
                except:
                    if pm.mode == 'DIALOG':
                        text and lh.spacer() or lh.blank()
                    elif pm.mode == 'PMENU':
                        lh.sep()

                # if p:
                #     try:
                #         exec(args)
                #     except:
                #         print(traceback.print_exc())
            else:
                text, icon, _, _, _ = pmi.parse()
                lh.operator(
                    WM_OT_pme_user_command_exec.bl_idname,
                    text, icon, cmd=pmi.text)

        elif pmi.mode == 'MENU':
            mouse_over, menu_name = pmi.parse_menu_data()
            if mouse_over:
                if menu_name in pr.pie_menus and \
                        pr.pie_menus[menu_name].mode == 'RMENU':
                    text, icon, _, _, _ = pmi.parse()
                    lh.menu(pmi.rm_class, text, icon)
                    # lh.menu(pr.pie_menus[menu_name].rm_class, text, icon)

            elif pmi.text in pr.pie_menus:
                sub_pm = pr.pie_menus[pmi.text]
                if sub_pm.mode == 'DIALOG':
                    sub_prop = pme.props.parse(sub_pm.data)
                    prop = pme.props.parse(pm.data)

                    if pm.mode == 'DIALOG' and prop.pd_expand:
                        lh.save()
                        lh.column()

                        draw_pme_layout(
                            pr.pie_menus[pmi.text], lh.layout,
                            WM_OT_pme_user_pie_menu_call._draw_item)

                        lh.restore()

                    elif sub_prop.pd_panel:
                        text, icon, _, _, _ = pmi.parse()
                        lh.operator(
                            WM_OT_pme_user_pie_menu_call.bl_idname,
                            text, icon, pie_menu_name=pmi.text,
                            invoke_mode='RELEASE')

                    elif pm.mode == 'PMENU':
                        WM_OT_pme_user_pie_menu_call._draw_slot(pmi.text)

                    else:
                        text, icon, _, _, _ = pmi.parse()
                        lh.operator(
                            WM_OT_pme_user_pie_menu_call.bl_idname,
                            text, icon, pie_menu_name=pmi.text,
                            invoke_mode='RELEASE')
                else:
                    invoke_mode = 'SUB' \
                        if pm.mode == 'PMENU' and sub_pm.mode == 'PMENU' \
                        else 'RELEASE'
                    text, icon, _, _, _ = pmi.parse()
                    lh.operator(
                        WM_OT_pme_user_pie_menu_call.bl_idname,
                        text, icon,
                        pie_menu_name=pmi.text, invoke_mode=invoke_mode)
            else:
                if pm.mode == 'DIALOG':
                    text, icon, _, _, _ = pmi.parse()
                    text and lh.spacer() or lh.blank()
                elif pm.mode == 'PMENU':
                    lh.sep()

        elif pmi.mode == 'PROP':
            text, _, prop = pmi.text.rpartition(".")
            obj = None
            bl_icon = None
            try:
                obj = eval(text)
            except:
                DBG and loge(traceback.format_exc())

            try:
                bl_icon = obj.bl_rna.properties[prop].icon
            except:
                pass

            text, icon, _, _, _ = pmi.parse()
            try:
                if bl_icon != 'NONE' or icon == 'NONE':
                    lh.prop(obj, prop, text)
                else:
                    lh.prop(obj, prop, text, icon)
            except:
                DBG and loge(traceback.format_exc())
                if pm.mode == 'DIALOG':
                    text and lh.spacer() or lh.blank()
                elif pm.mode == 'PMENU':
                    lh.sep()

        elif pmi.mode == 'HOTKEY':
            text, icon, _, _, _ = pmi.parse()
            lh.operator(
                WM_OT_pme_hotkey_call.bl_idname,
                text, icon,
                hotkey=pmi.text)

        elif pmi.mode == 'CUSTOM':
            text, icon, _, _, _ = pmi.parse()
            icon, icon_value = lh.parse_icon(icon)
            pme.context.layout = lh.layout
            pme.context.text = text
            pme.context.icon = icon
            pme.context.icon_value = icon_value

            try:
                exec(pmi.text, pme.context.globals, pme.context.gen_locals())
            except:
                traceback.print_exc()
                if pm.mode == 'DIALOG':
                    text and lh.spacer() or lh.blank()
                elif pm.mode == 'PMENU':
                    lh.sep()

    def _draw_pm(self, menu, context):
        pr = prefs()
        pm = pr.pie_menus[self.pie_menu_name]

        lh.lt(
            menu.layout.menu_pie(),
            operator_context='INVOKE_DEFAULT')

        for idx, pmi in enumerate(pm.pmis):
            if pmi.mode == 'EMPTY':
                lh.sep()
                continue

            WM_OT_pme_user_pie_menu_call._draw_item(pr, pm, pmi, idx)

    def _draw_rm(self, menu, context):
        pr = prefs()
        pm = pr.pie_menus[self.pie_menu_name]

        row = menu.layout.row()
        lh.column(row, operator_context='INVOKE_DEFAULT')

        for idx, pmi in enumerate(pm.pmis):
            if pmi.mode == 'EMPTY':
                if pmi.text == "":
                    lh.sep()
                elif pmi.text == "spacer":
                    lh.label(" ")
                elif pmi.text == "column":
                    lh.column(row, operator_context='INVOKE_DEFAULT')
                elif pmi.text == "label":
                    text, icon, _, _, _ = pmi.parse()
                    lh.label(text, icon)
                continue

            WM_OT_pme_user_pie_menu_call._draw_item(pr, pm, pmi, idx)

    @staticmethod
    def _draw_slot(name):
        pm = prefs().pie_menus[name]
        prop = pme.props.parse(pm.data)

        lh.save()
        layout = lh.layout
        if prop.pd_box:
            column = layout.box()
        else:
            column = layout
        layout = lh.column(column)

        draw_pme_layout(pm, layout, WM_OT_pme_user_pie_menu_call._draw_item)

        lh.restore()

    def _draw_popup_dialog(self, menu, context):
        pm = prefs().pie_menus[self.pie_menu_name]
        prop = pme.props.parse(pm.data)

        layout = menu.layout.menu_pie()
        layout.separator()
        layout.separator()

        if prop.pd_box:
            column = layout.box()
        else:
            column = layout
        column = column.column(align=True)
        lh.lt(column)

        draw_pme_layout(pm, column, WM_OT_pme_user_pie_menu_call._draw_item)

    def cancel(self, context):
        pass

    def check(self, context):
        return True

    def modal(self, context, event):
        pr = prefs()
        pm = pr.pie_menus[self.pie_menu_name]
        # if not pp.parse(pm.data).pm_flick:
        #     context.window.cursor_warp(self.x, self.y)

        if event.value == 'RELEASE' and \
                event.type == self.__class__.pressed_key:
            if self.hold_timer:
                if self.pm_press:
                    DBG and logi("HOLD - RELEASE", self)
                    if self.pm_press.mode == 'PMENU':
                        self.pm_press = None

                    elif self.pm_press.mode == 'DIALOG':
                        prop = pme.props.parse(self.pm_press.data)
                        if not prop.pd_panel:
                            self.pm_press = None

                    elif self.pm_press.mode == 'SCRIPT':
                        self._execute_script(self.pm_press)

                    elif self.pm_press.mode == 'STICKY':
                        self.pm_press = None

                    elif self.pm_press.mode == 'MACRO':
                        execute_macro(self.pm_press)

                    else:
                        bpy.ops.wm.pme_user_pie_menu_call(
                            'INVOKE_DEFAULT', pie_menu_name=self.pm_press.name,
                            invoke_mode='RELEASE')
                else:
                    DBG and logi("HOLD - DEFAULT", self)
                    keymap_helper.run_operator(
                        context, pm.key,
                        pm.ctrl, pm.shift, pm.alt, pm.oskey, pm.key_mod)

                self.hold_timer = None
                self.__class__.hold_inst = None
                return self.modal_stop()

            self.key_is_released = True
            self.__class__.pressed_key = None
            return {'PASS_THROUGH'}

        elif event.type == 'TIMER':
            if self.hold_timer and (
                    self.hold_timer.finished() or self.hold_timer.update()):

                if self.__class__.hold_inst == self:
                    self.__class__.hold_inst = None

                self.hold_timer = None
                self.modal_stop()
                self.executed = True
                if not self.cancelled:
                    bpy.ops.wm.pme_user_pie_menu_call(
                        'INVOKE_DEFAULT', pie_menu_name=self.pm_hold.name,
                        invoke_mode='HOLD')
                return {'CANCELLED'}

            if self.pm_timer and (
                    self.pm_timer.finished() or self.pm_timer.update()):
                if self.key_is_released:
                    DBG and logi("RELEASE", self)
                    for op in self.__class__.active_ops.values():
                        DBG and logi("-", op.pie_menu_name)
                        op.key_is_released = True

                if self.key_is_released or self.cancelled:
                    if self.cancelled:
                        DBG and logi("CANCELLED", self)
                    pr.pie_menu_prefs.restore()
                    self.pm_timer = None
                    return self.modal_stop()

            if self.bl_timer and self.bl_timer.time_duration > 5:
                if self.pm_timer:
                    pr.pie_menu_prefs.restore()
                    self.pm_timer = None
                return self.modal_stop()

        if pm.mode == 'PMENU' and not pme.props.parse(pm.data).pm_flick and \
                self.invoke_mode == 'HOTKEY':
            return {'RUNNING_MODAL'}

        return {'PASS_THROUGH'}

    def modal_start(self):
        wm = bpy.context.window_manager
        self.bl_timer = wm.event_timer_add(0.05, bpy.context.window)
        wm.modal_handler_add(self)
        DBG and logi("START", self)
        if self.pie_menu_name in self.__class__.active_ops:
            self.__class__.active_ops[self.pie_menu_name].cancelled = True
        self.__class__.active_ops[self.pie_menu_name] = self
        return {'RUNNING_MODAL'}

    def modal_stop(self):
        DBG and logi("STOP", self)
        bpy.context.window_manager.event_timer_remove(self.bl_timer)
        self.bl_timer = None
        if self.pie_menu_name in self.__class__.active_ops and \
                self.__class__.active_ops[self.pie_menu_name] == self:
            del self.__class__.active_ops[self.pie_menu_name]
        return {'CANCELLED'}

    def stop(self):
        self.cancelled = True

    def _execute_script(self, pm):
        prop = pme.props.parse(pm.data)
        if len(pm.pmis) == 1:
            pmi = pm.pmis[0]
            StackKey.reset()

        else:
            pmi = StackKey.next(pm)

        pme.context.exec_locals = StackKey.exec_locals

        try:
            if prop.s_undo and not StackKey.is_first:
                bpy.ops.ed.undo()

            if pmi.mode == 'HOTKEY':
                keymap_helper.run_operator_by_hotkey(bpy.context, pmi.text)
            elif pmi.mode == 'COMMAND':
                exec(
                    operator_utils.add_default_args(pmi.text),
                    pme.context.globals, StackKey.exec_locals)

            if len(pm.pmis) > 1:
                bpy.ops.pme.overlay('INVOKE_DEFAULT', text=pmi.name)

        except:
            traceback.print_exc()

        if not bpy.context.active_operator:
            bpy.ops.pme.dummy('INVOKE_DEFAULT', True)

        if len(pm.pmis) > 1:
            selection_state.update()

    def execute(self, context):
        return {'CANCELLED'}

    def execute_menu(self, context, event):
        self.executed = True
        pme.context.reset()
        bl_context.reset(context)

        wm = context.window_manager
        pr = prefs()
        pm = pr.pie_menus[self.pie_menu_name]

        if pm.mode == 'PMENU':
            prop = pme.props.parse(pm.data)
            radius = int(prop.pm_radius)
            confirm = int(prop.pm_confirm)
            threshold = int(prop.pm_threshold)

            pr.pie_menu_prefs.save()
            if radius == -1:
                radius = pr.pie_menu_prefs.radius
            if confirm == -1:
                confirm = pr.pie_menu_prefs.confirm
            if threshold == -1:
                threshold = pr.pie_menu_prefs.threshold

            view = context.user_preferences.view
            view.pie_menu_radius = radius
            view.pie_menu_confirm = confirm
            view.pie_menu_threshold = threshold

            wm.popup_menu_pie(event, self._draw_pm, pm.name)

            DBG and logi("SHOW", self)
            self.pm_timer = Timer(0.1 + view.pie_animation_timeout / 100)

            # if self.mouse_button_mod:
            #     update_mouse_state(self.mouse_button_mod)
            # elif is_mouse_button_pressed(pm.key):
            #     update_mouse_state(pm.key)

            return self.modal_start()

        elif pm.mode == 'RMENU':
            prop = pme.props.parse(pm.data)
            if prop.rm_title:
                context.window_manager.popup_menu(self._draw_rm, pm.name)
            else:
                context.window_manager.popup_menu(self._draw_rm)

        elif pm.mode == 'DIALOG':
            prop = pme.props.parse(pm.data)
            if prop.pd_panel:
                bpy.ops.wm.pme_user_dialog_call(
                    'INVOKE_DEFAULT', pie_menu_name=self.pie_menu_name)
            else:
                popup_dialog_pie(event, self._draw_popup_dialog)

        elif pm.mode == 'SCRIPT':
            self._execute_script(pm)

        elif pm.mode == 'STICKY':
            bpy.ops.pme.sticky_key('INVOKE_DEFAULT', pm_name=pm.name)

        elif pm.mode == 'MACRO':
            execute_macro(pm)

        # if self.mouse_button_mod:
        #     update_mouse_state(self.mouse_button_mod)
        # elif is_mouse_button_pressed(pm.key):
        #     update_mouse_state(pm.key)

        return {'CANCELLED'}

    def __str__(self):
        return "%s (%s)" % (self.pie_menu_name, self.invoke_mode)

    def _parse_open_mode(self, pm):
        if pm.open_mode == 'HOLD':
            self.pm_hold = pm
        elif pm.open_mode == 'PRESS':
            self.pm_press = pm
        elif pm.open_mode == 'ONE_SHOT':
            self.pm_press = pm

    def invoke(self, context, event):
        pr = prefs()
        pme.context.last_operator = self
        pme.context.event = event

        if self.pie_menu_name not in pr.pie_menus:
            return {'CANCELLED'}

        cpm = pr.pie_menus[self.pie_menu_name]
        pme.context.pm = cpm

        if self.invoke_mode == 'HOTKEY' and \
                not cpm.poll(self.__class__, context):
            return {'PASS_THROUGH'}

        if cpm.open_mode == 'HOLD' and cpm.mode == 'STICKY' and \
                PME_OT_sticky_key.root_instance:
            return {'CANCELLED'}

        # if cpm.open_mode == 'ONE_SHOT' and event.value != 'RELEASE':
        #     if keymap_helper.is_pressed(event.type):
        #         return {'CANCELLED'}
        #     keymap_helper.mark_pressed(event)

        if self.invoke_mode == 'HOTKEY' and cpm.key_mod == 'NONE':
            cpm_key = keymap_helper.to_system_mouse_key(cpm.key, context)
            for pm in reversed(pr.pie_menus):
                if pm == cpm:
                    continue

                pm_key = keymap_helper.to_system_mouse_key(pm.key, context)
                if pm.enabled and \
                        pm_key == cpm_key and pm.ctrl == cpm.ctrl and \
                        pm.shift == cpm.shift and pm.alt == cpm.alt and \
                        pm.oskey == cpm.oskey and \
                        pm.key_mod in MOUSE_BUTTONS and \
                        is_key_pressed(pm.key_mod):
                    self.pie_menu_name = pm.name
                    cpm = pm
                    break

        self.mouse_button_mod = cpm.key_mod in MOUSE_BUTTONS and cpm.key_mod
        if self.mouse_button_mod:
            if cpm.key == self.mouse_button_mod:
                return {'CANCELLED'}

            if not is_key_pressed(cpm.key_mod):
                return {'PASS_THROUGH'}

            if self.__class__.hold_inst:
                self.__class__.hold_inst.stop()

        if self.invoke_mode == 'RELEASE':
            self.__class__.pressed_key = None
            for op in self.__class__.active_ops.values():
                op.key_is_released = True

        elif self.invoke_mode == 'HOTKEY':
            self.__class__.pressed_key = \
                keymap_helper.to_system_mouse_key(
                    event.type, context)

            if self.pie_menu_name in self.__class__.active_ops:
                apm = self.__class__.active_ops[self.pie_menu_name]
                if not apm.executed:
                    return {'CANCELLED'}

                self.__class__.active_ops[
                    self.pie_menu_name].cancelled = True

        self.pm_press, self.pm_hold = None, None
        self._parse_open_mode(cpm)

        if self.invoke_mode == 'HOTKEY':
            for pm in pr.pie_menus:
                if pm != cpm and pm.enabled and \
                        keymap_helper.compare_km_names(
                            pm.km_name, cpm.km_name) and \
                        pm.key == cpm.key and \
                        pm.ctrl == cpm.ctrl and \
                        pm.shift == cpm.shift and \
                        pm.alt == cpm.alt and \
                        pm.oskey == cpm.oskey and \
                        pm.key_mod == cpm.key_mod and \
                        pm.open_mode != cpm.open_mode:
                    self._parse_open_mode(pm)

        if cpm.mode == 'PMENU' and pr.restore_mouse_pos:
            if self.invoke_mode == 'HOLD' and cpm.open_mode == 'HOLD' or \
                    not PME_OT_restore_mouse_pos.inst:
                bpy.ops.pme.restore_mouse_pos(
                    'INVOKE_DEFAULT',
                    key=event.type, x=event.mouse_x, y=event.mouse_y)
            elif self.invoke_mode == 'SUB':
                inst = PME_OT_restore_mouse_pos.inst
                if inst:
                    bpy.ops.pme.restore_mouse_pos(
                        'INVOKE_DEFAULT',
                        key=inst.key, x=inst.x, y=inst.y)

        if cpm.open_mode == 'PRESS' and self.pm_hold:
            cpm = self.pm_hold
            self.pie_menu_name = self.pm_hold.name

        DBG and logi("INVOKE", self, cpm.open_mode)

        if self.invoke_mode == 'RELEASE':
            if self.pie_menu_name in self.__class__.active_ops:
                self.__class__.active_ops[self.pie_menu_name].cancelled = True

        self.executed = False
        self.pm_timer = None
        self.hold_timer = None
        self.cancelled = False
        self.key_is_released = self.__class__.pressed_key is None
        self.release_timer = None

        self.x = event.mouse_x
        self.y = event.mouse_y

        if self.invoke_mode == 'HOTKEY':
            if cpm.open_mode == 'HOLD':
                self.hold_timer = Timer(pr.hold_time / 1000)
                # if is_mouse_button_pressed(cpm.key):
                #     update_mouse_state(cpm.key)

                self.__class__.hold_inst = self
                return self.modal_start()

        return self.execute_menu(context, event)


class WM_OT_pme_user_dialog_call(bpy.types.Operator):
    bl_idname = "wm.pme_user_dialog_call"
    bl_label = ""
    # bl_options = {'REGISTER', 'UNDO'}
    bl_options = {'INTERNAL'}

    pie_menu_name = StringProperty()

    def check(self, context):
        return True

    def draw(self, context):
        pm = prefs().pie_menus[self.pie_menu_name]

        column = self.layout.column(True)
        lh.lt(column)

        draw_pme_layout(pm, column, WM_OT_pme_user_pie_menu_call._draw_item)

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        pr = prefs()
        if self.pie_menu_name not in pr.pie_menus:
            return {'CANCELLED'}
        pm = pr.pie_menus[self.pie_menu_name]

        prop = pme.props.parse(pm.data)
        # if prop.pd_auto_close:
        if False:
            return context.window_manager.invoke_props_popup(
                self, event)
        else:
            return context.window_manager.invoke_props_dialog(
                self, width=int(prop.pd_width))


class WM_OT_pme_keyconfig_wait(bpy.types.Operator):
    bl_idname = "wm.pme_keyconfig_wait"
    bl_label = ""
    bl_options = {'INTERNAL'}

    def modal(self, context, event):
        pr = prefs()
        if event.type == 'TIMER':
            keymaps = bpy.context.window_manager.keyconfigs.user.keymaps
            registered_kms = []
            for km in pr.missing_kms:
                if km in keymaps:
                    registered_kms.append(km)
            for km in registered_kms:
                pr.missing_kms.remove(km)

            if not pr.missing_kms or self.t.update():
                while pr.unregistered_pms:
                    pr.unregistered_pms.pop().register_hotkey()
                context.window_manager.event_timer_remove(self.timer)
                self.timer = None
                return {'FINISHED'}

        return {'PASS_THROUGH'}

    def execute(self, context):
        self.t = Timer(10)
        self.timer = context.window_manager.event_timer_add(
            0.1, context.window)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


class WM_OT_pmi_submenu_select(bpy.types.Operator):
    bl_idname = "wm.pmi_submenu_select"
    bl_label = ""
    bl_description = "Select a menu"
    bl_options = {'INTERNAL'}
    bl_property = "enumprop"

    def get_items(self, context):
        pr = prefs()
        return [(k, k, "") for k in sorted(pr.pie_menus.keys())]

    pm_item = IntProperty()
    enumprop = bpy.props.EnumProperty(items=get_items)

    def execute(self, context):
        pr = prefs()
        pm = pr.selected_pm
        pmi = pm.pmis[self.pm_item]
        pmi.mode = 'MENU'
        pmi.name = self.enumprop
        pmi.text = self.enumprop

        tag_redraw()

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.invoke_search_popup(self)
        return {'FINISHED'}


class PME_OT_addonpref_search(bpy.types.Operator):
    bl_idname = "pme.addonpref_search"
    bl_label = ""
    bl_options = {'INTERNAL'}
    bl_property = "enumprop"

    items = None

    def get_items(self, context):
        cl = PME_OT_addonpref_search
        if not cl.items:
            cl.items = []
            import addon_utils
            for addon in context.user_preferences.addons:
                if hasattr(addon.preferences, "draw"):
                    mod = addon_utils.addons_fake_modules.get(addon.module)
                    if not mod:
                        continue
                    info = addon_utils.module_bl_info(mod)
                    cl.items.append((addon.module, info["name"], ""))

        return cl.items

    enumprop = bpy.props.EnumProperty(items=get_items)

    def execute(self, context):
        pr = prefs()
        if pr.pmi_data.cmd:
            pr.pmi_data.cmd += "; "
        pr.pmi_data.cmd += \
            "O.pme.timeout(cmd=\"O.pme.userpref_show(addon='%s')\")" % \
            self.enumprop
        if pr.pmi_data.mode != 'COMMAND':
            pr.pmi_data.mode = 'COMMAND'

        sname = ""
        for item in PME_OT_addonpref_search.items:
            if item[0] == self.enumprop:
                sname = item[1]
                break

        pr.pmi_data.sname = sname

        tag_redraw()
        return {'FINISHED'}

    def invoke(self, context, event):
        self.__class__.items = None
        context.window_manager.invoke_search_popup(self)
        return {'FINISHED'}


class WM_OT_pme_custom_set(bpy.types.Operator):
    bl_idname = "wm.pme_custom_set"
    bl_label = ""
    bl_description = "Custom"
    bl_options = {'INTERNAL'}

    mode = bpy.props.EnumProperty(items=(
        ('LABEL', "Label", "", 'SYNTAX_OFF', 0),
        ('PALETTES', "Palettes", "", 'COLOR', 1),
        ('ACTIVE_PALETTE', "Active Palette", "", 'COLOR', 2),
        ('COLOR_PICKER', "Color Picker", "", 'COLOR', 3),
        ('BRUSH', "Brush", "", 'BRUSH_DATA', 4),
        ('BRUSH_COLOR', "Brush Color", "", 'COLOR', 5),
        ('BRUSH_COLOR2', "Brush Color 2", "", 'COLOR', 6),
        ('TEXTURE', "Texture", "", 'TEXTURE', 7),
        ('TEXTURE_MASK', "Texture Mask", "", 'TEXTURE', 8),
        ('RECENT_FILES', "Recent Files", "", 'OPEN_RECENT', 9),
        ('MODIFIERS', "Modifiers Panel", "", 'MODIFIER', 10),
    ))

    def execute(self, context):
        pr = prefs()
        pm = pr.selected_pm

        lt = "L.box()" if pm.mode == 'PMENU' else "L"
        sep = "L.separator()" if pm.mode == 'PMENU' else "None"

        if self.mode == 'LABEL':
            pr.pmi_data.custom = (
                "%s.label(text, icon=icon, icon_value=icon_value)"
            ) % lt

        if self.mode == 'PALETTES':
            pr.pmi_data.custom = (
                "ps = paint_settings(bl_context); "
                "%s.template_ID(ps, 'palette', new='palette.new') "
                "if ps else %s"
            ) % (lt, sep)
            pr.pmi_data.sname = "Palettes"

        elif self.mode == 'ACTIVE_PALETTE':
            pr.pmi_data.custom = (
                "ps = paint_settings(bl_context); "
                "%s.template_palette(ps, 'palette', color=True) "
                "if ps else %s"
            ) % (lt, sep)
            pr.pmi_data.sname = "Active Palette"

        elif self.mode == 'COLOR_PICKER':
            pr.pmi_data.custom = (
                "ps = paint_settings(bl_context); "
                "T.VIEW3D_PT_tools_brush.prop_unified_color_picker("
                "%s, bl_context, ps.brush, 'color') "
                "if ps and ps.brush else %s"
            ) % (lt, sep)
            pr.pmi_data.sname = "Color Picker"

        elif self.mode == 'BRUSH':
            pr.pmi_data.custom = (
                "ps = paint_settings(bl_context); "
                "%s.template_ID_preview(ps, "
                "'brush', new='brush.add', rows=3, cols=8) "
                "if ps else %s"
            ) % (lt, sep)
            pr.pmi_data.sname = "Brush"

        elif self.mode == 'BRUSH_COLOR':
            pr.pmi_data.custom = (
                "ps = paint_settings(bl_context); "
                "T.VIEW3D_PT_tools_brush.prop_unified_color("
                "%s, bl_context, ps.brush, 'color') "
                "if ps and ps.brush else %s"
            ) % (lt, sep)
            pr.pmi_data.sname = "Color"

        elif self.mode == 'BRUSH_COLOR2':
            pr.pmi_data.custom = (
                "ps = paint_settings(bl_context); "
                "T.VIEW3D_PT_tools_brush.prop_unified_color("
                "%s, bl_context, ps.brush, 'secondary_color') "
                "if ps and ps.brush else %s"
            ) % (lt, sep)
            pr.pmi_data.sname = "Secondary Color"

        elif self.mode == 'TEXTURE':
            pr.pmi_data.custom = (
                "ps = paint_settings(bl_context); "
                "%s.template_ID_preview(ps.brush, "
                "'texture', new='texture.new', rows=3, cols=8) "
                "if ps and ps.brush else %s"
            ) % (lt, sep)
            pr.pmi_data.sname = "Texture"

        elif self.mode == 'TEXTURE_MASK':
            pr.pmi_data.custom = (
                "ps = paint_settings(bl_context); "
                "%s.template_ID_preview(ps.brush, "
                "'mask_texture', new='texture.new', rows=3, cols=8) "
                "if ps and ps.brush else %s"
            ) % (lt, sep)
            pr.pmi_data.sname = "Texture Mask"

        elif self.mode == 'RECENT_FILES':
            pr.pmi_data.custom = (
                "L.menu('INFO_MT_file_open_recent', "
                "text, icon=icon, icon_value=icon_value)"
            )
            pr.pmi_data.sname = "Recent Files"
            pr.pmi_data.icon = 'OPEN_RECENT'

        elif self.mode == 'MODIFIERS':
            pr.pmi_data.custom = (
                "panel(T.DATA_PT_modifiers, frame=False, header=False)"
            )
            pr.pmi_data.sname = "Modifiers Panel"
            pr.pmi_data.icon = 'MODIFIER'

        return {'FINISHED'}


class WM_OT_script_pm_search(bpy.types.Operator):
    bl_idname = "wm.script_pm_search"
    bl_label = ""
    bl_options = {'INTERNAL'}
    bl_property = "enumprop"

    items = None

    def get_items(self, context):
        if not WM_OT_script_pm_search.items:
            items = []
            for pm in sorted(prefs().pie_menus.keys()):
                items.append((pm, pm, ""))

            WM_OT_script_pm_search.items = items

        return WM_OT_script_pm_search.items

    enumprop = bpy.props.EnumProperty(items=get_items)

    def execute(self, context):
        pr = prefs()
        pm = pr.selected_pm

        if pr.pmi_data.cmd:
            pr.pmi_data.cmd += "; "
        pr.pmi_data.cmd += "open_menu(\"%s\")" % self.enumprop
        if pr.pmi_data.mode != 'COMMAND':
            pr.pmi_data.mode = 'COMMAND'

        pr.pmi_data.sname = self.enumprop

        tag_redraw()
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.invoke_search_popup(self)
        return {'FINISHED'}


class WM_OT_pmi_operator_search(bpy.types.Operator):
    bl_idname = "wm.pmi_operator_search"
    bl_label = ""
    bl_description = "Select blender's operator"
    bl_options = {'INTERNAL'}
    bl_property = "operator"

    pm_item = pint()
    append = pbool()

    items = []

    def get_items(self, context):
        if not WM_OT_pmi_operator_search.items:
            items = []
            for op_module_name in dir(bpy.ops):
                op_module = getattr(bpy.ops, op_module_name)
                for op_submodule_name in dir(op_module):
                    op = getattr(op_module, op_submodule_name)
                    op_type_name = op.idname()
                    op_type = getattr(bpy.types, op_type_name)
                    if hasattr(op_type, "bl_label"):
                        op_name = op_type.bl_label
                    else:
                        op_name = op_type.bl_rna.name
                        idx = op_name.find("_OT_")
                        if idx != -1:
                            op_name = op_name[idx + 4:]

                    label = op_name or op_submodule_name
                    # if op_submodule_name != label:
                    #     label = "[%s] %s (%s)" % (
                    #         op_module_name.upper(), label, op_submodule_name)
                    # else:
                    label = "%s|%s" % (utitle(label), op_module_name.upper())

                    items.append((
                        "%s.%s" % (op_module_name, op_submodule_name),
                        label, ""))

            WM_OT_pmi_operator_search.items = items

        return WM_OT_pmi_operator_search.items

    operator = bpy.props.EnumProperty(items=get_items)

    def execute(self, context):
        pr = prefs()
        pm = pr.selected_pm
        pmi = pm.pmis[self.pm_item]

        op_module_name, _, op_submodule_name = self.operator.partition(".")
        op_module = getattr(bpy.ops, op_module_name)
        op = getattr(op_module, op_submodule_name)
        op_type_name = op.idname()
        op_type = getattr(bpy.types, op_type_name)
        op_name = operator_utils.get_op_label(op_type)

        if pr.mode == 'PMI':
            if not self.append:
                pr.pmi_data.cmd = ""
            if pr.pmi_data.cmd:
                pr.pmi_data.cmd += "; "
            pr.pmi_data.cmd += "bpy.ops.%s()" % self.operator
            if pr.pmi_data.mode != 'COMMAND':
                pr.pmi_data.mode = 'COMMAND'

            pr.pmi_data.sname = op_name if op_name else self.operator
        else:
            pmi.text = "bpy.ops.%s()" % self.operator
            pmi.mode = 'COMMAND'

            pmi.name = op_name if op_name else self.operator

        tag_redraw()
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.invoke_search_popup(self)
        return {'FINISHED'}


class WM_OT_pmi_panel_search(bpy.types.Operator):
    bl_idname = "wm.pmi_panel_search"
    bl_label = "Panel"
    bl_description = "Use blender's panel"
    bl_options = {'INTERNAL'}
    bl_property = "enumprop"

    pm_item = pint()

    items = None

    def get_items(self, context):
        if not WM_OT_pmi_panel_search.items:
            items = []
            for tp in bl_panel_types():
                tp_name = tp.__name__
                ctx, _, name = tp_name.partition("_PT_")
                label = hasattr(
                    tp, "bl_label") and tp.bl_label or name or tp_name
                label = "%s|%s" % (utitle(label), ctx)
                # if name:
                #     if name == label or utitle(name) == label:
                #         label = "%s|%s" % (utitle(label), ctx)
                #     else:
                #         label = "[%s] %s (%s)" % (ctx, label, name)

                items.append((tp_name, label, ""))

            WM_OT_pmi_panel_search.items = items

        return WM_OT_pmi_panel_search.items

    enumprop = bpy.props.EnumProperty(items=get_items)

    def execute(self, context):
        pr = prefs()
        tp = getattr(bpy.types, self.enumprop)
        frame = header = True

        if self.enumprop == "DATA_PT_modifiers" or \
                self.enumprop == "OBJECT_PT_constraints" or \
                self.enumprop == "BONE_PT_constraints":
            frame = header = False

        pr.pmi_data.custom = \
            "panel(T.%s, frame=%r, header=%r, expand=None)" % (
                self.enumprop, frame, header)

        sname = tp.bl_label if hasattr(
            tp, "bl_label") and tp.bl_label else self.enumprop
        if "_PT_" in sname:
            _, _, sname = sname.partition("_PT_")
            sname = utitle(sname)
        pr.pmi_data.sname = sname

        return {'CANCELLED'}

    def invoke(self, context, event):
        context.window_manager.invoke_search_popup(self)

        return {'FINISHED'}


class WM_OT_pmidata_hints_show(bpy.types.Operator):
    bl_idname = "wm.pmidata_hints_show"
    bl_label = ""
    bl_description = "Hints"
    bl_options = {'INTERNAL'}

    def _draw(self, menu, context):
        pr = prefs()
        lh.lt(menu.layout)
        row = lh.row()

        pm = pr.selected_pm
        mode = 'COMMAND' if pm.mode in {'SCRIPT', 'STICKY', 'MACRO'} else \
            pr.pmi_data.mode

        lh.column(row)
        lh.label("Variables", 'INFO')
        lh.sep()
        lh.label("C = bpy.context", 'LAYER_USED')
        lh.label("D = bpy.data", 'LAYER_USED')
        lh.label("T = bpy.types", 'LAYER_USED')
        lh.label("P = bpy.props", 'LAYER_USED')

        if mode == 'CUSTOM':
            lh.label("L = layout", 'LAYER_USED')
            lh.label("text", 'LAYER_USED')
            lh.label("icon", 'LAYER_USED')
            lh.label("icon_value", 'LAYER_USED')
        else:
            lh.label("O = bpy.ops", 'LAYER_USED')

        lh.column(row)
        lh.label("Functions", 'INFO')
        lh.sep()
        lh.label("execute_script(filepath)", 'LAYER_ACTIVE')

        if mode != 'CUSTOM':
            lh.label("open_menu(name)", 'LAYER_ACTIVE')

        if mode == 'CUSTOM':
            lh.label("paint_settings(context)", 'LAYER_ACTIVE')
            lh.label("panel(type, frame=True, header=True)", 'LAYER_ACTIVE')

    def execute(self, context):
        context.window_manager.popup_menu(self._draw)

        return {'FINISHED'}


class WM_OT_pmidata_specials_call(bpy.types.Operator):
    bl_idname = "wm.pmidata_specials_call"
    bl_label = ""
    bl_description = "Menu"
    bl_options = {'INTERNAL'}

    def _draw_command(self, menu, context):
        lh.lt(menu.layout, operator_context='INVOKE_DEFAULT')

        lh.operator(
            WM_OT_pmidata_hints_show.bl_idname, "Hints", 'QUESTION')

        lh.sep()

        pm_item = pme.context.edit_item_idx

        lh.operator(
            WM_OT_script_open.bl_idname,
            "External Script", 'FILE_FOLDER',
            pm_item=pm_item,
            filepath=prefs().scripts_filepath)

        lh.operator(
            WM_OT_pmi_operator_search.bl_idname,
            "Operator", 'BLENDER',
            pm_item=pm_item)

        lh.menu("PME_MT_screen_set", "Screen", icon='SPLITSCREEN')
        lh.menu("PME_MT_brush_set", "Brush", icon='BRUSH_DATA')

        lh.operator(
            PME_OT_addonpref_search.bl_idname,
            "Addon Preferences", 'SCRIPT')

        lh.operator(
            WM_OT_script_pm_search.bl_idname,
            "Menu", 'MOD_SKIN')

    def _draw_menu(self, menu, context):
        lh.lt(menu.layout, operator_context='INVOKE_DEFAULT')

        pr = prefs()
        data = pr.pmi_data
        if data.menu and data.menu in pr.pie_menus and \
                pr.pie_menus[data.menu].mode == 'RMENU':
            lh.prop(data, "xmenu", "Open On Mouse Over")

        lh.sep(check=True)

        lh.operator(
            WM_OT_pmi_menu_search.bl_idname,
            "Menu", 'BLENDER',
            pm_item=pme.context.edit_item_idx,
            mouse_over=False)
        lh.operator(
            WM_OT_pmi_menu_search.bl_idname,
            "Menu (Open on Mouse Over)", 'BLENDER',
            pm_item=pme.context.edit_item_idx,
            mouse_over=True)

    def _draw_custom(self, menu, context):
        lh.lt(menu.layout, operator_context='INVOKE_DEFAULT')

        lh.operator(
            WM_OT_pmidata_hints_show.bl_idname, "Hints", 'QUESTION')

        lh.sep()

        lh.operator(
            WM_OT_script_open.bl_idname,
            "External Script", 'FILE_FOLDER',
            pm_item=pme.context.edit_item_idx,
            filepath=prefs().scripts_filepath)

        lh.operator(
            WM_OT_pmi_panel_search.bl_idname,
            "Panel", 'MENU_PANEL',
            pm_item=pme.context.edit_item_idx)

        lh.menu("PME_MT_header_menu_set", "Header Menu", icon='FULLSCREEN')

        lh.sep()

        lh.layout.operator_menu_enum(
            WM_OT_pme_custom_set.bl_idname, "mode",
            "Examples", icon='COLLAPSEMENU')

    def _draw_operator(self, menu, context):
        lh.lt(menu.layout, operator_context='INVOKE_DEFAULT')

        lh.operator(
            WM_OT_pmi_operator_search.bl_idname,
            "Operator", 'BLENDER',
            pm_item=pme.context.edit_item_idx)

    def execute(self, context):
        pr = prefs()
        if pr.pmi_data.mode == 'COMMAND':
            context.window_manager.popup_menu(self._draw_command)
        elif pr.pmi_data.mode == 'MENU':
            context.window_manager.popup_menu(self._draw_menu)
        elif pr.pmi_data.mode == 'CUSTOM':
            context.window_manager.popup_menu(self._draw_custom)
        # elif pr.pmi_data.mode == 'OPERATOR':
        #     context.window_manager.popup_menu(self._draw_operator)

        return {'FINISHED'}


class WM_OT_pmi_menu_search(bpy.types.Operator):
    bl_idname = "wm.pmi_menu_search"
    bl_label = ""
    bl_description = "Select menu"
    bl_options = {'INTERNAL'}
    bl_property = "enumprop"

    pm_item = pint()
    mouse_over = pbool()

    items = None

    def get_items(self, context):
        if not WM_OT_pmi_menu_search.items:
            items = []
            for tp_name in dir(bpy.types):
                tp = getattr(bpy.types, tp_name)
                if issubclass(tp, bpy.types.Menu) and hasattr(tp, "bl_label"):
                    ctx, _, name = tp_name.partition("_MT_")
                    label = hasattr(
                        tp, "bl_label") and tp.bl_label or name or tp_name
                    label = "%s|%s" % (utitle(label), ctx)
                    # if name:
                    #     if name == label or utitle(name) == label:
                    #         label = "%s|%s" % (utitle(label), ctx)
                    #     else:
                    #         label = "[%s] %s (%s)" % (ctx, label, name)

                    items.append((tp_name, label, ""))

            WM_OT_pmi_menu_search.items = items

        return WM_OT_pmi_menu_search.items

    enumprop = bpy.props.EnumProperty(items=get_items)

    def execute(self, context):
        pr = prefs()
        pm = pr.selected_pm
        pmi = pm.pmis[self.pm_item]

        if self.mouse_over:
            cmd = "L.menu(\"%s\", text, icon=icon, icon_value=icon_value)" % \
                self.enumprop
            mode = 'CUSTOM'
        else:
            cmd = "bpy.ops.wm.call_menu(name=\"%s\")" % self.enumprop
            mode = 'COMMAND'

        typ = getattr(bpy.types, self.enumprop)
        name = typ.bl_label if typ.bl_label else self.enumprop

        if pr.mode == 'PMI':
            if self.mouse_over:
                pr.pmi_data.custom = cmd
            else:
                pr.pmi_data.cmd = cmd
            pr.pmi_data.mode = mode
            pr.pmi_data.sname = name
        else:
            pmi.text = cmd
            pmi.mode = mode
            pmi.name = name

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.invoke_search_popup(self)
        return {'FINISHED'}


class WM_OT_script_open(bpy.types.Operator):
    bl_idname = "wm.script_open"
    bl_label = "Open Script"
    bl_description = "Open external script"
    bl_options = {'INTERNAL'}

    filename_ext = ".py"
    filepath = StringProperty(subtype='FILE_PATH', default="*.py")
    filter_glob = StringProperty(default="*.py", options={'HIDDEN'})
    pm_item = IntProperty(default=-1, options={'SKIP_SAVE'})

    def draw(self, context):
        pass

    def execute(self, context):
        pr = prefs()

        filepath = os.path.normpath(self.filepath)
        pr.scripts_filepath = filepath

        if filepath.startswith(ADDON_PATH):
            filepath = os.path.relpath(filepath, ADDON_PATH)

        filename = os.path.basename(filepath)
        filename, _, _ = filename.rpartition(".")
        name = filename.replace("_", " ").strip().title()

        filepath = filepath.replace("\\", "/")
        cmd = "execute_script(\"%s\")" % filepath

        pm = pr.selected_pm
        if self.pm_item == -1:
            pm.poll_cmd = "return " + cmd

        else:
            pmi = pm.pmis[self.pm_item]

            if pr.mode == 'PMI':
                if pr.pmi_data.mode == 'COMMAND':
                    pr.pmi_data.cmd = cmd
                elif pr.pmi_data.mode == 'CUSTOM':
                    pr.pmi_data.custom = cmd

                pr.pmi_data.sname = name
            else:
                pmi.text = cmd
                pmi.name = name

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class UI_OT_copy_python_command_button(bpy.types.Operator):
    bl_idname = "ui.copy_python_command_button"
    bl_label = "Copy Python Command"
    bl_description = "Copy python command"

    def _draw(self, menu, context):
        layout = menu.layout
        layout.label("Can't copy from here")

    def execute(self, context):
        ret = {'FINISHED'}
        bpy.utils.unregister_class(UI_OT_copy_python_command_button)
        try:
            if 'CANCELLED' in bpy.ops.ui.copy_python_command_button():
                ret = {'CANCELLED'}
        except:
            ret = {'CANCELLED'}

        bpy.utils.register_class(UI_OT_copy_python_command_button)

        if 'CANCELLED' not in ret:
            self.report({'INFO'}, context.window_manager.clipboard)
            bpy.ops.wm.pm_edit('INVOKE_DEFAULT', clipboard=True)
        else:
            context.window_manager.popup_menu(
                self._draw, self.bl_label, 'ERROR')

        return ret


class WM_OT_pme_debug_mode_toggle(bpy.types.Operator):
    bl_idname = "wm.pme_debug_mode_toggle"
    bl_label = "Toggle Debug Mode"
    bl_description = "Toggle debug mode"

    def execute(self, context):
        bpy.app.debug_wm = not bpy.app.debug_wm
        mode = "Off"
        if bpy.app.debug_wm:
            mode = "On"
        self.report({'INFO'}, I_DEBUG % mode)
        tag_redraw()
        return {'CANCELLED'}


class WM_OT_pme_hotkey_call(bpy.types.Operator):
    bl_idname = "wm.pme_hotkey_call"
    bl_label = "Hotkey"

    hotkey = pstring()

    def execute(self, context):
        keymap_helper.run_operator_by_hotkey(context, self.hotkey)
        return {'FINISHED'}


class WM_OT_pm_hotkey_remove(bpy.types.Operator):
    bl_idname = "wm.pm_hotkey_remove"
    bl_label = ""
    bl_description = "Remove the hotkey"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        pm = prefs().selected_pm
        pm["key"] = 0
        pm["ctrl"] = False
        pm["shift"] = False
        pm["alt"] = False
        pm["oskey"] = False
        pm["key_mod"] = 0
        pm.update_keymap_item(context)

        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        pm = prefs().selected_pm
        return pm.key != 'NONE'
        # return pm.name in kmis_map and kmis_map[pm.name]


def register():
    pme.context.add_global("traceback", traceback)