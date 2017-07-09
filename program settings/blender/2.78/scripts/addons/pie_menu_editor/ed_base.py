import bpy
from .addon import prefs, temp_prefs
from .debug_utils import *
from .bl_utils import (
    RemoveItemOperator, find_context, re_prop, re_operator, bp
)
from .ui import (
    tag_redraw, shorten_str, gen_prop_name, gen_op_name, find_enum_args
)
from .ui_utils import get_pme_menu_class
from .macro_utils import update_macro
from .layout_helper import lh, draw_pme_layout
from .constants import ARROW_ICONS, SPACE_ITEMS, I_CLIPBOARD, I_CMD, ED_DATA
from .property_utils import to_py_value
from . import keymap_helper
from . import pme
from . import operator_utils
from .operators import (
    popup_dialog_pie,
    WM_OT_pm_select,
    WM_OT_pm_hotkey_remove,
    WM_OT_pme_debug_mode_toggle,
    WM_OT_script_open,
)


class WM_OT_pmi_type_select(bpy.types.Operator):
    bl_idname = "wm.pmi_type_select"
    bl_label = ""
    bl_description = "Select type of the item"
    bl_options = {'INTERNAL'}

    pm_item = bpy.props.IntProperty()
    text = bpy.props.StringProperty()
    mode = bpy.props.StringProperty()

    def _draw(self, menu, context):
        pm = prefs().selected_pm
        lh.lt(menu.layout)

        lh.operator(
            WM_OT_pmi_type_select.bl_idname, "Command",
            pm_item=self.pm_item,
            text=self.text,
            mode='COMMAND')

        if self.mode == 'PROP_ASK':
            lh.operator(
                WM_OT_pmi_type_select.bl_idname, "Property",
                pm_item=self.pm_item,
                text=self.text,
                mode='PROP')

            mo = re_prop.search(self.text)
            prop_path = mo.group(1) + mo.group(2)
            obj_path, _, prop_name = prop_path.rpartition(".")
            prop = None
            try:
                tp = type(eval(obj_path))
                prop = tp.bl_rna.properties[prop_name]
            except:
                pass

            if prop and prop.type == 'ENUM':
                lh.operator(
                    WM_OT_pmi_type_select.bl_idname, "Custom (Menu)",
                    pm_item=self.pm_item,
                    text=self.text,
                    mode='PROP_ENUM_MENU')

                if pm.mode != 'PMENU':
                    lh.operator(
                        WM_OT_pmi_type_select.bl_idname, "Custom (List)",
                        pm_item=self.pm_item,
                        text=self.text,
                        mode='PROP_ENUM')

                    # lh.operator(
                    #     WM_OT_pmi_type_select.bl_idname, "Custom (Expand)",
                    #     pm_item=self.pm_item,
                    #     text=self.text,
                    #     mode='PROP_ENUM_EXPAND')

        if self.mode == 'ENUM_ASK':
            lh.operator(
                WM_OT_pmi_type_select.bl_idname, "Custom (Menu)",
                pm_item=self.pm_item,
                text=self.text,
                mode='ENUM_MENU')

            if pm.mode != 'PMENU':
                lh.operator(
                    WM_OT_pmi_type_select.bl_idname, "Custom (List)",
                    pm_item=self.pm_item,
                    text=self.text,
                    mode='ENUM')

    def execute(self, context):
        if 'ASK' in self.mode:
            bpy.context.window_manager.popup_menu(
                self._draw, title="Select Type")
        else:
            pm = prefs().selected_pm
            pmi = pm.pmis[self.pm_item]

            if self.mode == 'COMMAND':
                pmi.mode = 'COMMAND'
                pmi.text = self.text
                mo = re_operator.search(self.text)
                if mo:
                    pmi.name = gen_op_name(mo)
                else:
                    mo = re_prop.search(self.text)
                    pmi.name, icon = gen_prop_name(mo)
                    if icon:
                        pmi.icon = icon

            elif self.mode == 'PROP':
                pmi.mode = 'PROP'
                mo = re_prop.search(self.text)
                pmi.text = mo.group(1) + mo.group(2)
                if pmi.text[-1] == "]":
                    pmi.text, _, _ = pmi.text.rpartition("[")
                pmi.name, icon = gen_prop_name(mo, True)
                if icon:
                    pmi.icon = icon

                if pm.mode == 'PMENU':
                    try:
                        obj, _, prop_name = pmi.text.rpartition(".")
                        prop = type(eval(obj)).bl_rna.properties[prop_name]
                        if prop.type != 'BOOLEAN' or len(
                                prop.default_array) > 1:
                            pmi.mode = 'CUSTOM'
                            pmi.text = "L.column().prop(%s, '%s', '')" % (
                                obj, prop_name)
                    except:
                        pass

            elif self.mode == 'PROP_ENUM':
                pmi.mode = 'CUSTOM'
                mo = re_prop.search(self.text)
                prop_path = mo.group(1) + mo.group(2)
                obj_path, _, prop_name = prop_path.rpartition(".")
                pmi.text = (
                               "L.props_enum(%s, '%s')"
                           ) % (obj_path, prop_name)
                pmi.name, icon = gen_prop_name(mo, True)
                if icon:
                    pmi.icon = icon

            elif self.mode == 'PROP_ENUM_MENU':
                pmi.mode = 'CUSTOM'
                mo = re_prop.search(self.text)
                prop_path = mo.group(1) + mo.group(2)
                obj_path, _, prop_name = prop_path.rpartition(".")
                pmi.text = (
                               "L.prop_menu_enum(%s, '%s', text, icon=icon)"
                           ) % (obj_path, prop_name)
                pmi.name, icon = gen_prop_name(mo, True)
                if icon:
                    pmi.icon = icon

            # elif self.mode == 'PROP_ENUM_EXPAND':
            #     pmi.mode = 'CUSTOM'
            #     mo = re_prop.search(self.text)
            #     prop_path = mo.group(1) + mo.group(2)
            #     obj_path, _, prop_name = prop_path.rpartition(".")
            #     pmi.text = (
            #         "L.prop(%s, '%s', '', expand=True)"
            #     ) % (obj_path, prop_name)
            #     pmi.name, icon = gen_prop_name(mo, True)
            #     if icon:
            #         pmi.icon = icon

            elif self.mode == 'ENUM':
                pmi.mode = 'CUSTOM'
                mo = re_operator.search(self.text)
                enum_args = find_enum_args(mo)
                pmi.text = \
                    "L.operator_enum(\"%s\", \"%s\")" % (
                        mo.group(1), enum_args[0])
                pmi.name = gen_op_name(mo)

            elif self.mode == 'ENUM_MENU':
                pmi.mode = 'CUSTOM'
                mo = re_operator.search(self.text)
                enum_args = find_enum_args(mo)
                pmi.text = (
                               "L.operator_menu_enum(\"%s\", \"%s\", "
                               "text=text, icon=icon)"
                           ) % (mo.group(1), enum_args[0])
                pmi.name = gen_op_name(mo)

        tag_redraw()

        return {'CANCELLED'}


def _edit_pmi(operator, text):
    pr = prefs()
    pm = pr.selected_pm

    if operator.new_script:
        pm = pr.add_pm('SCRIPT')
        pmi = pm.pmis[0]

    if not operator.add:
        pmi = pm.pmis[operator.pm_item]
    else:
        if pm.mode in {'RMENU', 'SCRIPT', 'MACRO'}:
            pm.pmis.add()
            if operator.pm_item != -1:
                pm.pmis.move(len(pm.pmis) - 1, operator.pm_item)
            pmi = pm.pmis[operator.pm_item]
            pmi.mode = 'COMMAND'

        elif pm.mode == 'DIALOG':
            pmi = pm.ed.add_pd_row(pm)

    if not text:
        operator.report({'INFO'}, I_CLIPBOARD)
    else:
        lines = text.split("\n")
        if len(lines) > 1:
            filtered = []
            for line in lines:
                if re_prop.search(line) or re_operator.search(line):
                    filtered.append(line)
            lines = filtered

        # if pm.mode == 'SCRIPT':
        #     pm.data = "; ".join(lines)
        #     tag_redraw()
        #     return

        len_lines = len(lines)
        if len_lines == 0:
            operator.report({'INFO'}, I_CMD)
        elif len_lines > 1:
            pmi.mode = 'COMMAND'
            pmi.text = "; ".join(lines)
            pmi.name = shorten_str(pmi.text)
        else:
            mo = re_operator.search(lines[0])
            if mo:
                if 'CUSTOM' in pm.ed.supported_slot_modes and \
                        find_enum_args(mo):
                    bpy.ops.wm.pmi_type_select(
                        pm_item=operator.pm_item,
                        text=lines[0], mode="ENUM_ASK")

                else:
                    name = gen_op_name(mo)
                    pmi.name = name
                    pmi.mode = 'COMMAND'
                    pmi.text = lines[0]

            else:
                mo = re_prop.search(lines[0])
                if mo:
                    # if mo.group(4) and "(" not in lines[0]:
                    if 'PROP' in pm.ed.supported_slot_modes and mo.group(4):
                        bpy.ops.wm.pmi_type_select(
                            pm_item=operator.pm_item,
                            text=lines[0], mode="PROP_ASK")
                    else:
                        pmi.name, icon = gen_prop_name(mo)
                        if icon:
                            pmi.icon = icon
                        pmi.mode = 'COMMAND'
                        pmi.text = lines[0]

                else:
                    operator.report({'INFO'}, I_CMD)

        if pm.mode == 'MACRO':
            update_macro(pm)

    tag_redraw()


class WM_OT_pmi_edit(bpy.types.Operator):
    bl_idname = "wm.pmi_edit"
    bl_label = ""
    bl_description = "Use selected actions"
    bl_options = {'INTERNAL'}

    pm_item = bpy.props.IntProperty()
    auto = bpy.props.BoolProperty()
    add = bpy.props.BoolProperty()
    new_script = bpy.props.BoolProperty()

    def execute(self, context):
        bpy.ops.info.report_copy()
        text = context.window_manager.clipboard
        if text:
            bpy.ops.info.select_all_toggle()

        text = text.strip("\n")

        _edit_pmi(self, text)

        return {'CANCELLED'}


class WM_OT_pmi_edit_clipboard(bpy.types.Operator):
    bl_idname = "wm.pmi_edit_clipboard"
    bl_label = ""
    bl_description = "Use button's action"
    bl_options = {'INTERNAL'}

    pm_item = bpy.props.IntProperty()
    auto = bpy.props.BoolProperty()
    add = bpy.props.BoolProperty()
    new_script = bpy.props.BoolProperty()

    def execute(self, context):
        text = context.window_manager.clipboard
        text = text.strip("\n")

        _edit_pmi(self, text)

        return {'CANCELLED'}


class WM_OT_pmi_edit_auto(bpy.types.Operator):
    bl_idname = "wm.pmi_edit_auto"
    bl_label = ""
    bl_description = "Use previous action"
    bl_options = {'INTERNAL'}

    ignored_operators = {
        "bpy.ops.wm.pm_edit",
        "bpy.ops.wm.pme_none",
        "bpy.ops.info.reports_display_update",
        "bpy.ops.info.select_all_toggle",
        "bpy.ops.info.report_copy",
        "bpy.ops.view3d.smoothview",
    }

    pm_item = bpy.props.IntProperty()
    add = bpy.props.BoolProperty()
    new_script = bpy.props.BoolProperty()

    def execute(self, context):
        ctx = find_context('INFO')
        area_type = not ctx and context.area.type
        args = []
        if ctx:
            args.append(ctx)
        else:
            context.area.type = 'INFO'

        bpy.ops.wm.pme_none()
        bpy.ops.info.select_all_toggle(*args)
        bpy.ops.info.report_copy(*args)
        text = context.window_manager.clipboard

        if not text:
            bpy.ops.info.select_all_toggle(*args)
            bpy.ops.info.report_copy(*args)

        text = context.window_manager.clipboard

        idx2 = len(text)

        while True:
            idx2 = text.rfind("\n", 0, idx2)
            if idx2 == -1:
                text = ""
                break

            idx1 = text.rfind("\n", 0, idx2 - 1)
            line = text[idx1 + 1:idx2]
            op = line[0:line.find("(")]
            if line.startswith("Debug mode"):
                continue
            if op not in self.ignored_operators:
                text = line
                break

        bpy.ops.info.select_all_toggle(*args)

        text = text.strip("\n")

        _edit_pmi(self, text)

        if area_type:
            context.area.type = area_type

        return {'CANCELLED'}


class WM_OT_pm_edit(bpy.types.Operator):
    bl_idname = "wm.pm_edit"
    bl_label = "Edit Menu"
    bl_description = "Edit the menu"

    auto = bpy.props.BoolProperty(default=True, options={'SKIP_SAVE'})
    clipboard = bpy.props.BoolProperty(options={'SKIP_SAVE'})

    def _draw_pm(self, menu, context):
        pm = prefs().selected_pm

        lh.lt(menu.layout)

        for idx, pmi in enumerate(pm.pmis):
            text, icon, _, _, _ = pmi.parse()
            if pmi.mode == 'EMPTY':
                text = ". . ."

            lh.operator(
                self.op_bl_idname, text, ARROW_ICONS[idx], pm_item=idx,
                add=False, new_script=False)

        lh.sep()

        lh.operator(
            self.op_bl_idname, "New Stack Key", 'MOD_SKIN',
            pm_item=-1, add=False, new_script=True)
        lh.operator(
            WM_OT_pm_select.bl_idname, None, 'COLLAPSEMENU',
            pm_name="", use_mode_icons=False)

    def _draw_rm(self, menu, context):
        pm = prefs().selected_pm

        row = menu.layout.row()
        lh.column(row)
        lh.label(pm.name, icon='MOD_BOOLEAN')
        lh.operator(
            self.op_bl_idname, "New Stack Key", 'MOD_SKIN',
            pm_item=-1, add=False, new_script=True)
        lh.operator(
            WM_OT_pm_select.bl_idname, None, 'COLLAPSEMENU',
            pm_name="", use_mode_icons=False)
        lh.sep()

        idx = -1
        for pmi in pm.pmis:
            idx += 1
            name = pmi.name
            icon = pmi.parse_icon()

            if pmi.mode == 'EMPTY':
                if pmi.text == "column":
                    lh.operator(
                        self.op_bl_idname, "New Item", 'ZOOMIN',
                        pm_item=idx, add=True, new_script=False)
                    lh.column(row)
                    lh.label(" ")
                    lh.label(" ")
                    lh.label(" ")
                    lh.sep()

                elif pmi.text == "":
                    lh.sep()

                elif pmi.text == "spacer":
                    lh.label(" ")

                elif pmi.text == "label":
                    lh.label(name, icon=icon)

                continue

            lh.operator(
                self.op_bl_idname, name, icon, pm_item=idx,
                add=False, new_script=False)

        lh.operator(
            self.op_bl_idname, "New Item", 'ZOOMIN',
            pm_item=-1, add=True, new_script=False)

    def _draw_debug(self, menu, context):
        lh.lt(menu.layout)
        lh.operator(
            WM_OT_pme_debug_mode_toggle.bl_idname, "Enable Debug Mode")

    def _draw_pd(self, menu, context):
        pr = prefs()
        pm = pr.selected_pm

        layout = menu.layout.menu_pie()
        layout.separator()
        layout.separator()
        column = layout.box()
        column = column.column(align=True)
        lh.lt(column)

        def draw_pmi(pr, pm, pmi, idx):
            text, icon, _, icon_only, hidden = pmi.parse()

            if not text and not hidden:
                if pmi.mode == 'CUSTOM' or pmi.mode == 'PROP' and (
                        pmi.is_expandable_prop() or icon == 'NONE'):
                    if icon_only and pmi.mode != 'CUSTOM':
                        text = "[%s]" % pmi.name if pmi.name else " "
                    else:
                        text = pmi.name if pmi.name else " "

            lh.operator(
                self.op_bl_idname, text, icon,
                pm_item=idx, add=False, new_script=False)

        draw_pme_layout(pm, column, draw_pmi)

        lh.lt(column)
        column = lh.column()
        column.scale_x = pr.button_scalex
        column.scale_y = 1
        lh.sep()
        lh.operator(
            self.op_bl_idname, "New Item", 'ZOOMIN',
            pm_item=-1, add=True, new_script=False)
        lh.operator(
            self.op_bl_idname, "New Stack Key", 'MOD_SKIN',
            pm_item=-1, add=False, new_script=True)
        lh.operator(
            WM_OT_pm_select.bl_idname, None, 'COLLAPSEMENU',
            pm_name="", use_mode_icons=False)

    def _draw_script(self, menu, context):
        pm = prefs().selected_pm

        lh.lt(menu.layout)

        for idx, pmi in enumerate(pm.pmis):
            text, _, _, _, _ = pmi.parse()
            lh.operator(
                self.op_bl_idname, text, 'MOD_SKIN', pm_item=idx,
                add=False, new_script=False)

        lh.operator(
            self.op_bl_idname, "New Command", 'ZOOMIN',
            pm_item=-1, add=True, new_script=False)

        lh.sep()

        lh.operator(
            self.op_bl_idname, "New Stack Key", 'MOD_SKIN',
            pm_item=-1, add=False, new_script=True)
        lh.operator(
            WM_OT_pm_select.bl_idname, None, 'COLLAPSEMENU',
            pm_name="", use_mode_icons=False)

    def _draw_sticky(self, menu, context):
        pm = prefs().selected_pm

        lh.lt(menu.layout)

        for idx, pmi in enumerate(pm.pmis):
            text, _, _, _, _ = pmi.parse()
            lh.operator(
                self.op_bl_idname, text,
                'MESH_CIRCLE' if idx == 0 else 'SOLID',
                pm_item=idx,
                add=False, new_script=False)

        lh.sep()

        lh.operator(
            self.op_bl_idname, "New Stack Key", 'MOD_SKIN',
            pm_item=-1, add=False, new_script=True)
        lh.operator(
            WM_OT_pm_select.bl_idname, None, 'COLLAPSEMENU',
            pm_name="", use_mode_icons=False)

    def _draw_panel(self, menu, context):
        lh.lt(menu.layout)

        lh.operator(
            self.op_bl_idname, "New Stack Key", 'MOD_SKIN',
            pm_item=-1, add=False, new_script=True)
        lh.operator(
            WM_OT_pm_select.bl_idname, None, 'COLLAPSEMENU',
            pm_name="", use_mode_icons=False)

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        pr = prefs()
        if len(pr.pie_menus) == 0:
            bpy.ops.wm.pm_select(pm_name="")
            return {'CANCELLED'}
        pm = pr.selected_pm

        self.op_bl_idname = WM_OT_pmi_edit.bl_idname
        if self.clipboard:
            self.op_bl_idname = WM_OT_pmi_edit_clipboard.bl_idname
        elif self.auto:
            self.op_bl_idname = WM_OT_pmi_edit_auto.bl_idname

        if not bpy.app.debug_wm:
            bpy.context.window_manager.popup_menu(
                self._draw_debug, title="Debug Mode")

        elif pm.mode == 'DIALOG':
            popup_dialog_pie(event, self._draw_pd)

        elif pm.mode == 'PMENU':
            bpy.context.window_manager.popup_menu(
                self._draw_pm,
                title=pm.name)

        elif pm.mode == 'RMENU':
            bpy.context.window_manager.popup_menu(self._draw_rm)

        elif pm.mode == 'SCRIPT':
            bpy.context.window_manager.popup_menu(
                self._draw_script, title=pm.name)

        elif pm.mode == 'STICKY':
            bpy.context.window_manager.popup_menu(
                self._draw_sticky, title=pm.name)

        elif pm.mode == 'MACRO':
            bpy.context.window_manager.popup_menu(
                self._draw_script, title=pm.name)

        elif pm.mode == 'PANEL' or pm.mode == 'HPANEL':
            bpy.context.window_manager.popup_menu(
                self._draw_panel, title=pm.name)

        return {'FINISHED'}


class PME_OT_pmi_remove(RemoveItemOperator, bpy.types.Operator):
    bl_idname = "pme.pmi_remove"

    def get_collection(self):
        return prefs().selected_pm.pmis

    def finish(self):
        prefs().update_tree()
        tag_redraw()


class PME_OT_pmi_cmd_generate(bpy.types.Operator):
    bl_idname = "pme.pmi_cmd_generate"
    bl_label = "Generate Command"
    bl_description = "Generate command"

    clear = bpy.props.BoolProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        pr = prefs()
        data = pr.pmi_data

        if self.clear:
            for k in data.kmi.properties.keys():
                del data.kmi.properties[k]

        if pr.mode == 'PMI' and data.mode == 'COMMAND':
            op_idname, _, pos_args = operator_utils.find_operator(data.cmd)

            args = []
            for k in data.kmi.properties.keys():
                v = getattr(data.kmi.properties, k)
                value = to_py_value(data.kmi.properties, k, v)
                if value is None or isinstance(value, dict) and not value:
                    continue
                args.append("%s=%s" % (k, repr(value)))

            if len(pos_args) > 3:
                pos_args.clear()

            pos_args = [pos_args[0]] \
                if pos_args and isinstance(eval(pos_args[0]), dict) \
                else []
            if data.cmd_ctx != 'INVOKE_DEFAULT' or data.cmd_undo:
                pos_args.append(repr(data.cmd_ctx))
            if data.cmd_undo:
                pos_args.append(repr(data.cmd_undo))

            if pos_args and args:
                pos_args.append("")

            cmd = "bpy.ops.%s(%s%s)" % (
                op_idname, ", ".join(pos_args), ", ".join(args))

            if DBG_CMD_EDITOR:
                data.cmd = cmd
            else:
                data["cmd"] = cmd

        return {'PASS_THROUGH'}


class WM_OT_pmi_data_edit(bpy.types.Operator):
    bl_idname = "wm.pmi_data_edit"
    bl_label = "Edit Item (PME)"
    bl_description = "Edit the item"

    idx = bpy.props.IntProperty()
    ok = bpy.props.BoolProperty(options={'SKIP_SAVE'})
    hotkey = bpy.props.BoolProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        pr = prefs()
        tpr = temp_prefs()

        if self.hotkey:
            if pr.mode != 'PMI' or \
                    self.ok and pr.pmi_data.has_messages():
                return {'PASS_THROUGH'}

        pm = pr.selected_pm
        pmi = pm.pmis[self.idx]
        data = pr.pmi_data

        if self.idx == -1:
            data.info("")
            pr.leave_mode()
            tag_redraw()
            return {'FINISHED'}

        if self.ok:
            pr.leave_mode()
            self.idx = pme.context.edit_item_idx

            if not data.has_messages():
                pmi.mode = data.mode
                if data.mode == 'COMMAND':
                    pmi.text = data.cmd

                elif data.mode == 'PROP':
                    pmi.text = data.prop

                elif data.mode == 'MENU':
                    pmi.text = data.menu

                    if pmi.text and pmi.text in pr.pie_menus and \
                            pr.pie_menus[pmi.text].mode == 'RMENU' and \
                            data.xmenu:
                        get_pme_menu_class(pmi.text)
                        pmi.text = "@" + pmi.text

                elif data.mode == 'HOTKEY':
                    pmi.text = keymap_helper.to_hotkey(
                        data.key, data.ctrl, data.shift, data.alt,
                        data.oskey, data.key_mod)

                elif data.mode == 'CUSTOM':
                    pmi.text = data.custom

                    # elif data.mode == 'OPERATOR':
                    #     pmi.text = data.custom

            pmi.name = data.name
            pmi.icon = data.icon

            if pm.mode == 'MACRO':
                update_macro(pm)

            # if pmi.mode != 'PROP' and "#" in pmi.icon:
            #     pmi.icon = pmi.icon.replace("#", "")

            if pm.mode == 'SCRIPT':
                keymap_helper.StackKey.reset()

            pr.update_tree()

            tag_redraw()
            return {'FINISHED'}

        pme.context.edit_item_idx = self.idx
        pr.enter_mode('PMI')

        tpr.update_pie_menus()

        data.sname = ""
        data.mode = pmi.mode if pmi.mode != 'EMPTY' else 'COMMAND'
        data.name = pmi.name
        data.icon = pmi.icon

        data.cmd = pmi.text if data.mode == 'COMMAND' else ""
        data.custom = pmi.text if data.mode == 'CUSTOM' else ""
        data.prop = pmi.text if data.mode == 'PROP' else ""
        data.menu = pmi.text if data.mode == 'MENU' else ""
        data.xmenu = False
        if data.menu and data.menu[0] == "@":
            data.xmenu = True
            data.menu = data.menu[1:]

        data.key, data.ctrl, data.shift, data.alt, \
            data.oskey, data.key_mod = \
            'NONE', False, False, False, False, 'NONE'
        if pmi.mode == 'HOTKEY':
            data.key, data.ctrl, data.shift, data.alt, \
                data.oskey, data.key_mod = keymap_helper.parse_hotkey(pmi.text)

        data.check_pmi_errors(context)

        tag_redraw()

        return {'FINISHED'}


class WM_OT_pmi_icon_tag_toggle(bpy.types.Operator):
    bl_idname = "wm.pmi_icon_tag_toggle"
    bl_label = ""
    bl_description = ""
    bl_options = {'INTERNAL'}

    idx = bpy.props.IntProperty()
    tag = bpy.props.StringProperty()

    def execute(self, context):
        pm = prefs().selected_pm
        pmi = pm.pmis[self.idx]

        pmi.icon = pmi.icon.replace(self.tag, "") \
            if self.tag in pmi.icon else self.tag + pmi.icon

        tag_redraw()

        return {'FINISHED'}


class WM_OT_pmi_icon_select(bpy.types.Operator):
    bl_idname = "wm.pmi_icon_select"
    bl_label = "Select Icon (PME)"
    bl_description = "Select an icon"
    bl_options = {'INTERNAL'}

    idx = bpy.props.IntProperty()
    icon = bpy.props.StringProperty(options={'SKIP_SAVE'})
    hotkey = bpy.props.BoolProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        pr = prefs()

        if self.hotkey and pr.mode != 'ICONS':
            return {'PASS_THROUGH'}

        if self.idx == -1:  # Cancel
            pr.leave_mode()
            tag_redraw()
            return {'FINISHED'}

        pm = pr.selected_pm
        pmi = pm.pmis[self.idx]

        data = pmi
        if pr.is_edit_mode():
            data = pr.pmi_data

        if not self.icon:
            if data.mode == 'PROP':
                text = data.prop if hasattr(data, "prop") else data.text
                bl_prop = bp.get(text)
                if bl_prop and bl_prop.icon != 'NONE':
                    return {'FINISHED'}
            pme.context.edit_item_idx = self.idx
            pr.enter_mode('ICONS')

            tag_redraw()
            return {'FINISHED'}
        else:
            icon = self.icon
            _, icon_only, hidden = data.extract_flags()
            if icon_only:
                icon = "#" + icon
            if hidden:
                icon = "!" + icon
            data.icon = icon if self.icon != 'NONE' else ""
            pr.leave_mode()

        tag_redraw()
        return {'FINISHED'}


class PME_MT_header_menu_set(bpy.types.Menu):
    bl_label = "Menu"

    def draw(self, context):
        lh.save()
        lh.lt(self.layout)

        for id, name, _, icon, _ in SPACE_ITEMS:
            if id == 'CURRENT':
                lh.sep()

            lh.operator(
                "wm.pme_user_command_exec", name, icon,
                cmd=(
                    "d = prefs().pmi_data; "
                    "d.custom = 'header_menu([\"{0}\"])'; "
                    "d.sname = '{1}'; "
                    "d.icon = '{2}'"
                ).format(id, name, icon))

        lh.operator(
            "wm.pme_user_command_exec", name, icon,
            cmd=(
                "d = prefs().pmi_data; "
                "d.custom = 'header_menu([\"CURRENT\"])'; "
                "d.sname = 'Current Area'; "
                "d.icon = 'BLENDER'"
            ))

        lh.restore()


class PME_MT_screen_set(bpy.types.Menu):
    bl_label = "Menu"

    icons = {
        "3D View Full": 'FULLSCREEN',
        "Animation": 'NLA',
        "Compositing": 'NODETREE',
        "Default": 'VIEW3D',
        "Game Logic": 'LOGIC',
        "Motion Tracking": 'RENDER_ANIMATION',
        "Scripting": 'TEXT',
        "UV Editing": 'IMAGE_COL',
        "Video Editing": 'SEQUENCE',
    }

    def draw(self, context):
        lh.save()
        lh.lt(self.layout)

        for name in sorted(bpy.data.screens.keys()):
            if name == "temp":
                continue
            icon = 'NONE' if name not in PME_MT_screen_set.icons else \
                PME_MT_screen_set.icons[name]

            lh.operator(
                "wm.pme_user_command_exec", name, icon,
                cmd=(
                    "d = prefs().pmi_data; "
                    "d.cmd = 'bpy.ops.pme.screen_set(name=\"{0}\")'; "
                    "d.sname = '{0}'; "
                    "d.icon = '{1}'"
                ).format(name, icon))

        lh.restore()


class PME_MT_brush_set(bpy.types.Menu):
    bl_label = "Menu"

    def draw(self, context):
        brushes = bpy.data.brushes
        lh.save()

        def add_brush(col, brush):
            brush = brushes[brush]

            col.operator(
                "wm.pme_user_command_exec",
                brush.name, icon='LAYER_ACTIVE').cmd = (
                "d = prefs().pmi_data; "
                "d.cmd = 'paint_settings(C).brush = D.brushes[\"{0}\"]'; "
                "d.sname = '{0}'; "
                "d.icon = '{1}'"
            ).format(brush.name, 'BRUSH_DATA')

        image_brushes = []
        sculpt_brushes = []
        vertex_brushes = []
        weight_brushes = []
        for name in sorted(brushes.keys()):
            brush = brushes[name]
            brush.use_paint_image and image_brushes.append(brush.name)
            brush.use_paint_sculpt and sculpt_brushes.append(brush.name)
            brush.use_paint_vertex and vertex_brushes.append(brush.name)
            brush.use_paint_weight and weight_brushes.append(brush.name)

        row = self.layout.row()
        col_image = row.column()
        col_image.label("Image", icon='TPAINT_HLT')
        col_image.separator()
        for brush in image_brushes:
            add_brush(col_image, brush)

        col_vertex = row.column()
        col_vertex.label("Vertex", icon='VPAINT_HLT')
        col_vertex.separator()
        for brush in vertex_brushes:
            add_brush(col_vertex, brush)

        col_weight = row.column()
        col_weight.label("Weight", icon='WPAINT_HLT')
        col_weight.separator()
        for brush in weight_brushes:
            add_brush(col_weight, brush)

        col_sculpt = row.column()
        col_sculpt.label("Sculpt", icon='SCULPTMODE_HLT')
        col_sculpt.separator()
        for brush in sculpt_brushes:
            add_brush(col_sculpt, brush)

        lh.restore()


class PME_OT_keymap_add(bpy.types.Operator):
    bl_idname = "pme.keymap_add"
    bl_label = ""
    bl_description = "Add a keymap"
    bl_options = {'INTERNAL'}
    bl_property = "enumprop"

    items = None

    def get_items(self, context):
        cl = PME_OT_keymap_add
        if not cl.items:
            it1 = []
            it2 = []
            pr = prefs()
            pm = pr.selected_pm

            for km in context.window_manager.keyconfigs.user.keymaps:
                has_hotkey = False
                for kmi in km.keymap_items:
                    if kmi.idname and kmi.type != 'NONE' and \
                            kmi.type == pm.key and \
                            kmi.ctrl == pm.ctrl and \
                            kmi.shift == pm.shift and \
                            kmi.alt == pm.alt and \
                            kmi.oskey == pm.oskey and \
                            kmi.key_modifier == pm.key_mod:
                        has_hotkey = True
                        break

                if has_hotkey:
                    it1.append((km.name, "%s (%s)" % (km.name, kmi.name), ""))
                else:
                    it2.append((km.name, km.name, ""))

            it1.sort()
            it2.sort()

            cl.items = [t for t in it1]
            cl.items.extend([t for t in it2])

        return cl.items

    enumprop = bpy.props.EnumProperty(items=get_items)

    def execute(self, context):
        pr = prefs()
        pm = pr.selected_pm
        km_names = pm.parse_keymap()
        if self.enumprop not in km_names:
            # names = parse_keymap(pm.km_name)
            names = list(km_names)
            if len(names) == 1 and names[0] == "Window":
                names.clear()
            names.append(self.enumprop)
            names.sort()
            pm.km_name = ", ".join(names)

        tag_redraw()
        return {'FINISHED'}

    def invoke(self, context, event):
        PME_OT_keymap_add.items = None
        context.window_manager.invoke_search_popup(self)
        return {'FINISHED'}


class PME_OT_pm_open_mode_select(bpy.types.Operator):
    bl_idname = "pme.pm_open_mode_select"
    bl_label = "Open Mode"
    bl_description = "Select open mode"

    def _draw(self, menu, context):
        layout = menu.layout
        pm = prefs().selected_pm
        layout.prop(pm, "open_mode", expand=True)
        # if 'PRESS' in pm.ed.supported_open_modes:
        #     layout.prop_enum(pm, "open_mode", 'PRESS', icon='BLENDER')
        # if 'HOLD' in pm.ed.supported_open_modes:
        #     layout.prop_enum(pm, "open_mode", 'HOLD')
        # if 'DOUBLE_CLICK' in pm.ed.supported_open_modes:
        #     layout.prop_enum(pm, "open_mode", 'DOUBLE_CLICK')
        # if 'ONE_SHOT' in pm.ed.supported_open_modes:
        #     layout.prop_enum(pm, "open_mode", 'ONE_SHOT')

    def execute(self, context):
        context.window_manager.popup_menu(
            self._draw, PME_OT_pm_open_mode_select.bl_label)
        return {'FINISHED'}


# class WM_OT_pm_hotkey_convert(bpy.types.Operator):
#     bl_idname = "wm.pm_hotkey_convert"
#     bl_label = ""
#     bl_options = {'INTERNAL'}
#     bl_description = "Replace the key with ActionMouse/SelectMouse"

#     def execute(self, context):
#         pm = prefs().selected_pm
#         if pm.key == 'LEFTMOUSE' or pm.key == 'RIGHTMOUSE':
#             pm.key = keymap_helper.to_blender_mouse_key(pm.key, context)

#         return {'CANCELLED'}


class PME_OT_pmi_copy(bpy.types.Operator):
    bl_idname = "pme.pmi_copy"
    bl_label = "Copy Item"
    bl_description = "Copy an item"
    bl_options = {'INTERNAL'}

    pm_item = bpy.props.IntProperty()

    def execute(self, context):
        pr = prefs()
        pm = pr.selected_pm
        pmi = pm.pmis[self.pm_item]

        pmi.copy_item()

        return {'FINISHED'}


class PME_OT_pmi_paste(bpy.types.Operator):
    bl_idname = "pme.pmi_paste"
    bl_label = "Paste Item"
    bl_description = "Paste an item"
    bl_options = {'INTERNAL'}

    pm_item = bpy.props.IntProperty()

    def execute(self, context):
        pr = prefs()
        pm = pr.selected_pm
        pmi = pm.pmis[self.pm_item]

        if pr.pmi_clipboard[2] not in pm.ed.supported_slot_modes:
            self.report({'WARNING'}, "Can't paste here")
            return {'CANCELLED'}

        pmi.paste_item()

        if pm.mode == 'MACRO':
            update_macro(pm)

        pr.update_tree()
        tag_redraw()
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return prefs().pmi_clipboard is not None


class EditorBase:
    editors = {}

    def __init__(self):
        self.editors[self.id] = self

        for id, name, icon in ED_DATA:
            if id == self.id:
                self.default_name = name
                self.icon = icon
                break

        self.docs = None
        self.use_slot_icon = True
        self.use_preview = True
        self.sub_item = True
        self.has_hotkey = True
        self.has_extra_settings = True
        self.default_pmi_data = ""
        self.supported_slot_modes = {
            'EMPTY', 'COMMAND', 'PROP', 'MENU', 'HOTKEY', 'CUSTOM'
        }
        self.supported_open_modes = {
            'PRESS', 'HOLD', 'DOUBLE_CLICK', 'ONE_SHOT'
        }
        self.supported_sub_menus = {
            'PMENU', 'RMENU', 'DIALOG', 'SCRIPT', 'STICKY', 'MACRO'
        }

    def draw_extra_settings(self, layout, pm):
        row = layout.row(True)
        sub = row.row(True)
        sub.alert = pm.name in pm.poll_methods and \
            pm.poll_methods[pm.name] is None
        sub.prop(pm, "poll_cmd", "", icon='NODE_SEL')
        row.operator(
            WM_OT_script_open.bl_idname, "", icon='FILE_FOLDER',
        ).filepath = prefs().scripts_filepath

    def draw_keymap(self, layout, data):
        row = layout.row(True)
        if ',' in data.km_name:
            row.prop(data, "km_name", "", icon='SPLITSCREEN')
        else:
            row.prop_search(
                data, "km_name",
                bpy.context.window_manager.keyconfigs.user, "keymaps",
                "", icon='SPLITSCREEN')
        row.operator(PME_OT_keymap_add.bl_idname, "", icon='ZOOMIN')

    def draw_hotkey(self, layout, data):
        row = layout.row(align=True)
        item = None
        for i in data.__class__.open_mode[1]['items']:
            if i[0] == data.open_mode:
                item = i
                break

        subcol = row.column(True)
        subcol.scale_y = 2
        subcol.operator(
            PME_OT_pm_open_mode_select.bl_idname, "", icon=item[3])

        subcol = row.column(True)
        subrow = subcol.row(align=True)
        subrow.prop(data, "key", "", event=True)
        # if data.key == 'LEFTMOUSE' or data.key == 'RIGHTMOUSE':
        #     subrow.operator(
        #         WM_OT_pm_hotkey_convert.bl_idname, "",
        #         icon='RESTRICT_SELECT_OFF')
        subrow = subcol.row(align=True)
        subrow.prop(data, "ctrl", "Ctrl", toggle=True)
        subrow.prop(data, "shift", "Shift", toggle=True)
        subrow.prop(data, "alt", "Alt", toggle=True)
        subrow.prop(data, "oskey", "OSkey", toggle=True)
        subrow.prop(data, "key_mod", "", event=True)

        subcol = row.column(True)
        subcol.scale_y = 2
        subcol.operator(WM_OT_pm_hotkey_remove.bl_idname, icon='X')

    def draw_items(self, layout, pm):
        pass

    def draw_slot_modes(self, layout, slot):
        if 'COMMAND' in self.supported_slot_modes:
            layout.prop_enum(slot, "mode", 'COMMAND')
        if 'PROP' in self.supported_slot_modes:
            layout.prop_enum(slot, "mode", 'PROP')
        if 'MENU' in self.supported_slot_modes:
            layout.prop_enum(slot, "mode", 'MENU')
        if 'HOTKEY' in self.supported_slot_modes:
            layout.prop_enum(slot, "mode", 'HOTKEY')
        if 'CUSTOM' in self.supported_slot_modes:
            layout.prop_enum(slot, "mode", 'CUSTOM')
        # layout.prop(slot, "mode", expand=True)


def ed(id):
    return EditorBase.editors[id]
