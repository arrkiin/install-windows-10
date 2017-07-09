import bpy
import os
import json
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
from bpy_extras.io_utils import ExportHelper, ImportHelper
from .addon import (
    ADDON_ID, ADDON_PATH, SCRIPT_PATH, SAFE_MODE, prefs, temp_prefs)
from .constants import (
    ICON_OFF, ICON_ON, PM_ITEMS, PM_ITEMS_M, PM_ITEMS_M_DEFAULT, ED_DATA,
    OP_CTX_ITEMS,
    NUM_LIST_ROWS, LIST_PADDING, DEFAULT_POLL,
    W_FILE, W_JSON, W_KEY,
    SPACE_ITEMS, REGION_ITEMS, OPEN_MODE_ITEMS)
from .bl_utils import (
    bp, re_operator, re_prop, re_prop_set, re_name_idx,
    BaseCollectionItem
)
from .layout_helper import lh
from .debug_utils import *
from .panel_utils import (
    hide_panel, unhide_panel, add_panel,
    hidden_panel, rename_panel_group, remove_panel_group,
    panel_context_items, bl_panel_types)
from .macro_utils import (
    add_macro, remove_macro, rename_macro)
from . import keymap_helper
from . import pme
from . import operator_utils
from .keymap_helper import (
    KeymapHelper, MOUSE_BUTTONS,
    add_mouse_button, remove_mouse_button, to_key_name)
from .operators import (
    WM_OT_pm_select, WM_OT_pme_user_pie_menu_call,
    WM_OT_pmidata_specials_call
)
from .extra_operators import PME_OT_none
from .previews_helper import ph
from .ui import (
    tag_redraw, draw_addons_maximized, is_userpref_maximized,
    gen_op_name, gen_prop_name
)
from .ui_utils import get_pme_menu_class, pme_menu_classes
from . import ed_pie_menu
from . import ed_menu
from . import ed_popup
from . import ed_stack_key
from . import ed_sticky_key
from . import ed_macro
from . import ed_panel_group
from . import ed_hpanel_group
from .ed_base import (
    WM_OT_pmi_icon_select, WM_OT_pmi_data_edit, WM_OT_pm_edit,
    PME_OT_pmi_cmd_generate
)
from .ed_panel_group import (
    PME_OT_interactive_panels_toggle, draw_pme_panel, poll_pme_panel)
from .ed_sticky_key import PME_OT_sticky_key_edit

EDITORS = dict(
    PMENU=ed_pie_menu.Editor(),
    RMENU=ed_menu.Editor(),
    DIALOG=ed_popup.Editor(),
    SCRIPT=ed_stack_key.Editor(),
    STICKY=ed_sticky_key.Editor(),
    MACRO=ed_macro.Editor(),
    PANEL=ed_panel_group.Editor(),
    HPANEL=ed_hpanel_group.Editor(),
)

TREE_SPLITTER = '$PME$'

MAP_TYPES = ['KEYBOARD', 'MOUSE', 'TWEAK', 'NDOF', 'TEXTINPUT', 'TIMER']

EMODE_ITEMS = [
    ('COMMAND', "Command", "Python code"),
    ('PROP', "Property", "Property"),
    ('MENU', "Menu", "Sub-menu"),
    ('HOTKEY', "Hotkey", "Hotkey"),
    ('CUSTOM', "Custom", "Custom layout"),
    # ('OPERATOR', "Operator", "Operator"),
]
MODE_ITEMS = [
    ('EMPTY', "Empty", "Don't use the item")
]
MODE_ITEMS.extend(EMODE_ITEMS)
PD_MODE_ITEMS = (
    ('PIE', 'Pie Mode', ""),
    ('PANEL', 'Panel Mode', ""),
)

AVAILABLE_ICONS = {}

for k, i in bpy.types.UILayout.bl_rna.functions[
        "prop"].parameters["icon"].enum_items.items():
    if k != 'NONE':
        AVAILABLE_ICONS[i.identifier] = True


pp = pme.props
kmis_map = {}
import_filepath = os.path.join(ADDON_PATH, "examples", "examples.json")
export_filepath = os.path.join(ADDON_PATH, "examples", "my_pie_menus.json")


class WM_OT_pm_import(bpy.types.Operator, ImportHelper):
    bl_idname = "wm.pm_import"
    bl_label = "Import Menus"
    bl_description = "Import menus"
    bl_options = {'INTERNAL'}

    filename_ext = ".json"
    filepath = StringProperty(subtype='FILE_PATH', default="*.json")
    files = CollectionProperty(type=bpy.types.OperatorFileListElement)
    filter_glob = StringProperty(default="*.json", options={'HIDDEN'})
    directory = StringProperty(subtype='DIR_PATH')
    mode = StringProperty()

    def _draw(self, menu, context):
        lh.lt(menu.layout, operator_context='INVOKE_DEFAULT')

        lh.operator(
            WM_OT_pm_import.bl_idname, "Rename if exists",
            filepath=import_filepath,
            mode='RENAME')

        lh.operator(
            WM_OT_pm_import.bl_idname, "Skip if exists",
            filepath=import_filepath,
            mode='SKIP')

        lh.operator(
            WM_OT_pm_import.bl_idname, "Replace if exists",
            filepath=import_filepath,
            mode='REPLACE')

    def draw(self, context):
        pass

    def import_file(self, filepath):
        try:
            with open(filepath, 'r') as f:
                s = f.read()
        except:
            self.report({'WARNING'}, W_FILE)
            return

        menus = None
        try:
            menus = json.loads(s)
        except:
            self.report({'WARNING'}, W_JSON)
            return

        if menus:
            pr = prefs()

            if self.mode == 'RENAME':
                pm_names = [menu[0] for menu in menus]
                new_names = {}

                for name in pm_names:
                    if name in pr.pie_menus:
                        new_names[name] = pr.unique_pm_name(name)

            for menu in menus:
                if self.mode == 'REPLACE':
                    if menu[0] in pr.pie_menus:
                        pr.remove_pm(pr.pie_menus[menu[0]])
                elif self.mode == 'RENAME':
                    if menu[0] in new_names:
                        menu[0] = new_names[menu[0]]
                elif self.mode == 'SKIP':
                    if menu[0] in pr.pie_menus:
                        continue

                mode = menu[4] if len(menu) > 4 else 'PMENU'
                pm = pr.add_pm(mode, menu[0], True)
                pm.km_name = menu[1]

                n = len(menu)
                if n > 5:
                    pm.data = menu[5]
                if n > 6:
                    pm.open_mode = menu[6]
                if n > 7:
                    pm.poll_cmd = menu[7]

                if menu[2]:
                    try:
                        (pm.key, pm.ctrl, pm.shift, pm.alt, pm.oskey,
                         pm.key_mod) = keymap_helper.parse_hotkey(menu[2])
                    except:
                        self.report({'WARNING'}, W_KEY % menu[2])

                items = menu[3]
                for i in range(0, len(items)):
                    item = items[i]
                    pmi = pm.pmis[i] if mode == 'PMENU' else pm.pmis.add()
                    n = len(item)
                    if n == 4:
                        if self.mode == 'RENAME' and \
                                item[1] == 'MENU' and item[3] in new_names:
                            item[3] = new_names[item[3]]

                        try:
                            pmi.mode = item[1]
                        except:
                            pmi.mode = 'EMPTY'

                        pmi.name = item[0]
                        pmi.icon = item[2]
                        pmi.text = item[3]

                    elif n == 3:
                        pmi.mode = 'EMPTY'
                        pmi.name = item[0]
                        pmi.icon = item[1]
                        pmi.text = item[2]

                    elif n == 1:
                        pmi.mode = 'EMPTY'
                        pmi.text = item[0]

                if pm.mode == 'SCRIPT' and not pm.data.startswith("s?"):
                    pmi = pm.pmis.add()
                    pmi.text = pm.data
                    pmi.mode = 'COMMAND'
                    pmi.name = "Command 1"
                    pm.data = pm.ed.default_pmi_data

            for menu in menus:
                pm = pr.pie_menus[menu[0]]
                if pm.mode == 'PANEL':
                    for i, pmi in enumerate(pm.pmis):
                        add_panel(
                            pm.name, i, pmi.text, pmi.name,
                            pm.panel_space, pm.panel_region,
                            pm.panel_context, pm.panel_category,
                            draw_pme_panel, poll_pme_panel)

                elif pm.mode == 'HPANEL':
                    for pmi in pm.pmis:
                        hide_panel(pmi.text)

                elif pm.mode == 'MACRO':
                    add_macro(pm)

    def execute(self, context):
        global import_filepath

        for f in self.files:
            filepath = os.path.join(self.directory, f.name)
            if os.path.isfile(filepath):
                self.import_file(filepath)

        import_filepath = self.filepath

        PME_UL_pm_tree.update_tree()

        return {'FINISHED'}

    def invoke(self, context, event):
        if not self.mode:
            context.window_manager.popup_menu(
                self._draw, title=self.bl_description)
            return {'FINISHED'}

        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class WM_OT_pm_export(bpy.types.Operator, ExportHelper):
    bl_idname = "wm.pm_export"
    bl_label = "Export Menus"
    bl_description = "Export menus"
    bl_options = {'INTERNAL', 'REGISTER', 'UNDO'}

    filename_ext = ".json"
    filepath = StringProperty(subtype='FILE_PATH', default="*.json")
    filter_glob = StringProperty(default="*.json", options={'HIDDEN'})
    mode = StringProperty()

    def _draw(self, menu, context):
        lh.lt(menu.layout, operator_context='INVOKE_DEFAULT')

        lh.operator(
            WM_OT_pm_export.bl_idname, "All Menus",
            filepath=export_filepath,
            mode='ALL')

        lh.operator(
            WM_OT_pm_export.bl_idname, "All Enabled Menus",
            filepath=export_filepath,
            mode='ENABLED')

        lh.operator(
            WM_OT_pm_export.bl_idname, "Selected Menu",
            filepath=export_filepath,
            mode='ACTIVE')

    def check(self, context):
        return True

    def draw(self, context):
        return

    def execute(self, context):
        global export_filepath

        pr = prefs()

        if not self.filepath:
            return {'CANCELLED'}

        if not self.filepath.endswith(".json"):
            self.filepath += ".json"

        menus = []
        apm = pr.selected_pm
        apm_name = apm and apm.name

        pms_to_export = set()
        parsed_pms = set()

        def parse_children(pmis):
            for pmi in pmis:
                if pmi.mode == 'MENU':
                    _, menu_name = pmi.parse_menu_data()
                    if menu_name in pr.pie_menus:
                        pms_to_export.add(menu_name)
                        if menu_name not in parsed_pms:
                            parsed_pms.add(menu_name)
                            parse_children(pr.pie_menus[menu_name].pmis)

        for pm in pr.pie_menus:
            if self.mode == 'ENABLED' and not pm.enabled:
                continue
            if self.mode == 'ACTIVE' and pm.name != apm_name:
                continue
            pms_to_export.add(pm.name)
            parsed_pms.add(pm.name)

            if self.mode != 'ALL':
                parse_children(pm.pmis)

        for pm_name in pms_to_export:
            pm = pr.pie_menus[pm_name]
            items = []

            for pmi in pm.pmis:
                if pmi.mode == 'EMPTY':
                    if pmi.name:
                        item = (pmi.name, pmi.icon, pmi.text)
                    else:
                        item = (pmi.text,)
                else:
                    item = (
                        pmi.name,
                        pmi.mode,
                        pmi.icon,
                        pmi.text
                    )
                items.append(item)

            menu = (
                pm.name,
                pm.km_name,
                pm.to_hotkey(use_key_names=False),
                items,
                pm.mode,
                pm.data,
                pm.open_mode,
                pm.poll_cmd
            )
            menus.append(menu)

        try:
            with open(self.filepath, 'w') as f:
                f.write(json.dumps(menus, indent=2, separators=(", ", ": ")))
        except:
            return {'CANCELLED'}

        export_filepath = self.filepath
        return {'FINISHED'}

    def invoke(self, context, event):
        if not self.mode:
            context.window_manager.popup_menu(
                self._draw, title=self.bl_description)
            return {'FINISHED'}

        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class WM_OT_pm_add(bpy.types.Operator):
    bl_idname = "wm.pm_add"
    bl_label = ""
    bl_description = "Add an item"
    bl_options = {'INTERNAL'}

    mode = StringProperty()

    def _draw(self, menu, context):
        PME_MT_pm_new.draw_items(self, menu.layout)

    def execute(self, context):
        if not self.mode:
            context.window_manager.popup_menu(
                self._draw, WM_OT_pm_add.bl_description)
        else:
            prefs().add_pm(self.mode)
            PME_UL_pm_tree.update_tree()
            tag_redraw()

        return {'CANCELLED'}


class WM_OT_pm_duplicate(bpy.types.Operator):
    bl_idname = "wm.pm_duplicate"
    bl_label = ""
    bl_description = "Duplicate the selected menu"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        pr = prefs()
        if len(pr.pie_menus) == 0:
            return {'FINISHED'}

        apm = pr.selected_pm
        apm_name = apm.name

        pm = pr.add_pm(apm.mode, apm_name, True)
        apm = pr.pie_menus[apm_name]

        pm.km_name = apm.km_name
        if pm.km_name in PME_UL_pm_tree.collapsed_km_names:
            PME_UL_pm_tree.collapsed_km_names.remove(pm.km_name)

        pm.mode = apm.mode
        pm.data = apm.data
        pm.open_mode = apm.open_mode
        pm.poll_cmd = apm.poll_cmd

        if pm.mode != 'HPANEL':
            for i in range(0, len(apm.pmis)):
                if apm.mode != 'PMENU':
                    pm.pmis.add()

                pm.pmis[i].name = apm.pmis[i].name
                pm.pmis[i].icon = apm.pmis[i].icon
                pm.pmis[i].mode = apm.pmis[i].mode
                pm.pmis[i].text = apm.pmis[i].text

        if pm.mode == 'MACRO':
            add_macro(pm)
        elif pm.mode == 'PANEL':
            for i, pmi in enumerate(pm.pmis):
                add_panel(
                    pm.name, i, pmi.text, pmi.name,
                    pm.panel_space, pm.panel_region,
                    pm.panel_context, pm.panel_category,
                    draw_pme_panel, poll_pme_panel)
        elif pm.mode == 'HPANEL':
            pass

        PME_UL_pm_tree.update_tree()

        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return len(prefs().pie_menus) > 0


class WM_OT_pm_remove(bpy.types.Operator):
    bl_idname = "wm.pm_remove"
    bl_label = ""
    bl_description = "Remove the selected menu"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        prefs().remove_pm()
        PME_UL_pm_tree.update_tree()
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return len(prefs().pie_menus) > 0


class WM_OT_pm_remove_all(bpy.types.Operator):
    bl_idname = "wm.pm_remove_all"
    bl_label = ""
    bl_description = "Remove all menus"
    bl_options = {'INTERNAL'}

    ask = BoolProperty()

    def _draw(self, menu, context):
        lh.lt(menu.layout)
        lh.operator(
            WM_OT_pm_remove_all.bl_idname, "Remove All", 'X',
            ask=False)

    def execute(self, context):
        pr = prefs()
        if self.ask:
            context.window_manager.popup_menu(
                self._draw, WM_OT_pm_remove_all.bl_description, 'QUESTION')
        else:
            n = len(pr.pie_menus)
            for i in range(0, n):
                pr.remove_pm()

            PME_UL_pm_tree.update_tree()
            tag_redraw()

        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return len(prefs().pie_menus) > 0


class WM_OT_pm_enable_all(bpy.types.Operator):
    bl_idname = "wm.pm_enable_all"
    bl_label = ""
    bl_description = "Enable or disable all menus"
    bl_options = {'INTERNAL'}

    enabled = BoolProperty()

    def execute(self, context):
        for pm in prefs().pie_menus:
            pm.enabled = self.enabled
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return len(prefs().pie_menus) > 0


class WM_OT_pm_move(bpy.types.Operator):
    bl_idname = "wm.pm_move"
    bl_label = ""
    bl_description = "Move the selected menu"
    bl_options = {'INTERNAL'}

    direction = IntProperty()

    def execute(self, context):
        pr = prefs()
        tpr = temp_prefs()
        if pr.tree_mode:
            link = tpr.links[tpr.links_idx]
            if link.label:
                return {'CANCELLED'}

            new_idx = tpr.links_idx + self.direction
            num_links = len(tpr.links)
            if 0 <= new_idx <= num_links - 1:
                new_link = tpr.links[new_idx]
                if link.is_folder or not link.path:
                    while 0 <= new_idx < num_links:
                        new_link = tpr.links[new_idx]
                        if new_link.label:
                            return {'CANCELLED'}
                        elif not new_link.path:
                            break

                        new_idx += self.direction

                    if new_idx < 0 or new_idx >= num_links:
                        return {'CANCELLED'}

                else:
                    if new_link.label or new_link.is_folder or \
                            not new_link.path:
                        return {'CANCELLED'}

                pm_idx = pr.pie_menus.find(new_link.pm_name)
                pr.pie_menus.move(pr.active_pie_menu_idx, pm_idx)
                pr.active_pie_menu_idx = pm_idx
                PME_UL_pm_tree.update_tree()
                # PME.links_idx = new_idx

            else:
                return {'CANCELLED'}

        else:
            new_idx = pr.active_pie_menu_idx + self.direction
            if 0 <= new_idx <= len(pr.pie_menus) - 1:
                pr.pie_menus.move(pr.active_pie_menu_idx, new_idx)
                pr.active_pie_menu_idx = new_idx

            PME_UL_pm_tree.update_tree()
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return len(prefs().pie_menus) > 1


class WM_OT_pm_sort(bpy.types.Operator):
    bl_idname = "wm.pm_sort"
    bl_label = ""
    bl_description = "Sort menus"
    bl_options = {'INTERNAL'}

    mode = StringProperty()

    def _draw(self, menu, context):
        lh.lt(menu.layout)
        lh.operator(
            WM_OT_pm_sort.bl_idname, "By Name", 'SORTALPHA',
            mode='NAME')

        lh.operator(
            WM_OT_pm_sort.bl_idname, "By Hotkey", 'FONTPREVIEW',
            mode='HOTKEY')

        lh.operator(
            WM_OT_pm_sort.bl_idname, "By Keymap Name", 'SPLITSCREEN',
            mode='KEYMAP')

        lh.operator(
            WM_OT_pm_sort.bl_idname, "By Type", 'PROP_CON',
            mode='TYPE')

    def execute(self, context):
        if not self.mode:
            context.window_manager.popup_menu(
                self._draw, WM_OT_pm_sort.bl_description)
            return {'FINISHED'}

        pr = prefs()
        if len(pr.pie_menus) == 0:
            return {'FINISHED'}

        items = [pm for pm in pr.pie_menus]

        if self.mode == 'NAME':
            items.sort(key=lambda pm: pm.name)
        if self.mode == 'KEYMAP':
            items.sort(key=lambda pm: (pm.km_name, pm.name))
        if self.mode == 'HOTKEY':
            items.sort(key=lambda pm: (
                to_key_name(pm.key) if pm.key != 'NONE' else '_',
                pm.ctrl, pm.shift, pm.alt, pm.oskey,
                pm.key_mod if pm.key_mod != 'NONE' else '_'))
        if self.mode == 'TYPE':
            items.sort(key=lambda pm: (pm.mode, pm.name))

        items = [pm.name for pm in items]
        apm = pr.selected_pm
        apm_name = apm.name

        idx = len(items) - 1
        aidx = 0
        while idx > 0:
            k = items[idx]
            if pr.pie_menus[idx] != pr.pie_menus[k]:
                k_idx = pr.pie_menus.find(k)
                pr.pie_menus.move(k_idx, idx)
            if apm_name == k:
                aidx = idx
            idx -= 1
        pr.active_pie_menu_idx = aidx

        PME_UL_pm_tree.update_tree()

        tag_redraw()
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return len(prefs().pie_menus) > 1


class PME_MT_pm_new(bpy.types.Menu):
    bl_label = "New"

    def draw_items(self, layout):
        lh.lt(layout)

        for id, name, icon in ED_DATA:
            lh.operator(WM_OT_pm_add.bl_idname, name, icon, mode=id)

    def draw(self, context):
        self.draw_items(self.layout)


class WM_OT_pme_preview(bpy.types.Operator):
    bl_idname = "wm.pme_preview"
    bl_label = ""
    bl_description = "Preview"
    bl_options = {'INTERNAL'}

    pie_menu_name = StringProperty()

    def execute(self, context):
        bpy.ops.wm.pme_user_pie_menu_call(
            'INVOKE_DEFAULT', pie_menu_name=self.pie_menu_name,
            invoke_mode='RELEASE')
        return {'FINISHED'}


class PME_OT_pmi_name_apply(bpy.types.Operator):
    bl_idname = "pme.pmi_name_apply"
    bl_label = ""
    bl_description = "Apply the suggested name"
    bl_options = {'INTERNAL'}

    idx = bpy.props.IntProperty()

    def execute(self, context):
        data = prefs().pmi_data
        data.name = data.sname
        return {'FINISHED'}


class WM_OT_icon_filter_clear(bpy.types.Operator):
    bl_idname = "wm.icon_filter_clear"
    bl_label = ""
    bl_description = "Clear Filter"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        prefs().icon_filter = ""
        return {'FINISHED'}


class PME_OT_icons_refresh(bpy.types.Operator):
    bl_idname = "pme.icons_refresh"
    bl_label = ""
    bl_description = "Refresh icons"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        ph.refresh()
        return {'FINISHED'}


class PME_OT_docs(bpy.types.Operator):
    bl_idname = "pme.docs"
    bl_label = "Pie Menu Editor Documentation"
    bl_description = "Documentation"
    bl_options = {'INTERNAL'}

    id = bpy.props.StringProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        bpy.ops.wm.url_open(
            url=(
                "https://wiki.blender.org/index.php/User:Raa/"
                "Addons/Pie_Menu_Editor") + self.id)
        return {'FINISHED'}


class PMLink(bpy.types.PropertyGroup):
    pm_name = bpy.props.StringProperty()
    is_folder = bpy.props.BoolProperty()
    label = bpy.props.StringProperty()
    folder = bpy.props.StringProperty()
    group = bpy.props.StringProperty()

    idx = 0
    paths = {}

    @staticmethod
    def add():
        link = temp_prefs().links.add()
        link.name = str(PMLink.idx)
        PMLink.idx += 1
        return link

    @staticmethod
    def clear():
        PMLink.idx = 0
        PMLink.paths.clear()

    def __getattr__(self, attr):
        if attr == "path":
            if self.name not in PMLink.paths:
                PMLink.paths[self.name] = []
            return PMLink.paths[self.name]

    def __str__(self):
        return "%s [%s] (%r) (%s)" % (
            self.pm_name, "/".join(self.path), self.is_folder, self.label)

    def curpath(self):
        ret = self.group + TREE_SPLITTER
        ret += TREE_SPLITTER.join(self.path)
        return ret

    def fullpath(self):
        ret = self.group + TREE_SPLITTER
        ret += TREE_SPLITTER.join(self.path)
        if self.is_folder:
            if self.path:
                ret += TREE_SPLITTER
            ret += self.pm_name
        return ret


class PMEData(bpy.types.PropertyGroup):
    def get_links_idx(self):
        return self["links_idx"] if "links_idx" in self else 0

    def set_links_idx(self, value):
        pr = prefs()
        tpr = temp_prefs()

        if value < 0 or value >= len(tpr.links):
            return
        link = tpr.links[value]

        self["links_idx"] = value
        if link.pm_name:
            pr.active_pie_menu_idx = pr.pie_menus.find(link.pm_name)

    links = bpy.props.CollectionProperty(type=PMLink)
    links_idx = bpy.props.IntProperty(get=get_links_idx, set=set_links_idx)
    hidden_panels_idx = bpy.props.IntProperty()
    pie_menus = bpy.props.CollectionProperty(type=BaseCollectionItem)

    def update_pie_menus(self):
        pr = prefs()
        spm = pr.selected_pm
        supported_sub_menus = spm.ed.supported_sub_menus
        pms = set()

        for pm in pr.pie_menus:
            if pm.name == spm.name:
                continue
            if pm.mode in supported_sub_menus:
                pms.add(pm.name)

        self.pie_menus.clear()
        for pm in sorted(pms):
            item = self.pie_menus.add()
            item.name = pm


class WM_UL_panel_list(bpy.types.UIList):

    def draw_item(
            self, context, layout, data, item,
            icon, active_data, active_propname, index):
        tp = hidden_panel(item.text)
        v = prefs().panel_info_visibility
        if 'NAME' in v:
            layout.label(item.name or item.text, icon='SYNTAX_OFF')
        if 'CLASS' in v:
            layout.label(item.text, icon='SYNTAX_ON')
        if 'CTX' in v:
            layout.label(
                tp.bl_context if tp and hasattr(tp, "bl_context") else "-",
                icon='NODE')
        if 'CAT' in v:
            layout.label(
                tp.bl_category if tp and hasattr(tp, "bl_category") else "-",
                icon='LINENUMBERS_ON')


class WM_UL_pm_list(bpy.types.UIList):

    def draw_item(
            self, context, layout, data, item,
            icon, active_data, active_propname, index):
        pr = prefs()
        layout = layout.row(True)

        layout.prop(
            item, "enabled", text="", emboss=False,
            icon=ICON_ON if item.enabled else ICON_OFF)

        layout.label(icon=item.ed.icon)

        col = 0
        num_cols = pr.show_names + pr.show_hotkeys + pr.show_keymap_names

        if pr.show_names:
            layout.prop(
                item, "label", text="", emboss=False)
            col += 1

        if pr.show_hotkeys:
            if num_cols == 2 and col == 1:
                layout = layout.row(True)
                layout.alignment = 'RIGHT'
            layout.label(item.to_hotkey())
            col += 1

        if pr.show_keymap_names:
            if num_cols == 2 and col == 1:
                layout = layout.row(True)
                layout.alignment = 'RIGHT'
            layout.label(item.km_name)

    # def draw_filter(self, context, layout):
    #     layout = layout.row(True)
    #     layout.prop(
    #         prefs(), "show_hotkeys", icon='FONTPREVIEW', toggle=True)
    #     layout.prop(
    #         prefs(), "show_keymap_names", icon='SPLITSCREEN', toggle=True)

    def filter_items(self, context, data, propname):
        pr = prefs()
        pie_menus = getattr(data, propname)
        helper_funcs = bpy.types.UI_UL_list

        filtered = []
        ordered = []

        if self.filter_name:
            filtered = helper_funcs.filter_items_by_name(
                self.filter_name, self.bitflag_filter_item,
                pie_menus, "name")

        if not filtered:
            filtered = [self.bitflag_filter_item] * len(pie_menus)

        if pr.use_filter:
            for idx, pm in enumerate(pie_menus):
                if not pm.filter(pr):
                    filtered[idx] = 0

        if self.use_filter_sort_alpha:
            ordered = helper_funcs.sort_items_by_name(pie_menus, "name")

        return filtered, ordered


class PME_UL_pm_tree(bpy.types.UIList):
    locked = False
    collapsed_km_names = set()
    expanded_folders = set()
    keymap_names = None
    has_folders = False

    @staticmethod
    def link_is_collapsed(link):
        path = link.path
        p = link.group
        for i in range(0, len(path)):
            if p:
                p += TREE_SPLITTER
            p += path[i]
            if p not in PME_UL_pm_tree.expanded_folders:
                return True
        return False

    @staticmethod
    def update_tree():
        if PME_UL_pm_tree.locked:
            return

        pr = prefs()

        if not pr.tree_mode:
            return

        tpr = temp_prefs()

        DBG_TREE and logh("Update Tree")
        num_links = len(tpr.links)
        sel_link, sel_folder = None, None
        sel_link = 0 <= tpr.links_idx < num_links and tpr.links[tpr.links_idx]
        if not sel_link or not sel_link.pm_name or \
                sel_link.pm_name not in pr.pie_menus:
            sel_link = None
        sel_folder = sel_link and sel_link.path and sel_link.path[-1]

        tpr.links.clear()
        PMLink.clear()

        folders = {}
        keymaps = {}
        files = set()

        pms = [
            pm for pm in pr.pie_menus
            if not pr.use_filter or pm.filter(pr)]
        if pr.show_keymap_names:
            pms.sort(key=lambda pm: pm.km_name)
        else:
            keymaps["dummy"] = True
            pms.sort(key=lambda pm: pm.name)

        for pm in pms:
            if pr.show_keymap_names:
                kms = pm.km_name.split(", ")
                for km in kms:
                    if km not in keymaps:
                        keymaps[km] = []
                    keymaps[km].append(pm)

            for pmi in pm.pmis:
                if pmi.mode == 'MENU':
                    _, name = pmi.parse_menu_data()
                    if name not in pr.pie_menus or \
                            pr.use_filter and \
                            not pr.pie_menus[name].filter(pr):
                        continue

                    if pm.name not in folders:
                        folders[pm.name] = []

                    folders[pm.name].append(name)
                    files.add(name)

        PME_UL_pm_tree.has_folders = len(folders) > 0

        if pr.show_keymap_names:
            for kpms in keymaps.values():
                kpms.sort(key=lambda pm: pm.name)

        def add_children(files, group, path, idx, aidx):
            DBG_TREE and logi(" " * len(path) + "/".join(path))
            for file in files:
                if file in path:
                    continue
                link = PMLink.add()
                link.group = group
                link.pm_name = file
                link.folder = pm.name
                link.path.extend(path)
                if file == apm_name and (
                        not sel_link or sel_folder == pm.name):
                    aidx = idx
                idx += 1

                if file in folders:
                    link.is_folder = True
                    path.append(file)
                    new_idx, aidx = add_children(
                        folders[file], group, path, idx, aidx)
                    if new_idx == idx:
                        link.is_folder = False
                    idx = new_idx
                    path.pop()

            return idx, aidx

        idx = 0
        aidx = -1
        apm_name = len(pr.pie_menus) and pr.selected_pm.name

        PME_UL_pm_tree.keymap_names = \
            km_names = sorted(keymaps.keys())

        for km in km_names:
            if pr.show_keymap_names:
                link = PMLink.add()
                link.label = km
                idx += 1

                pms = keymaps[km]

            path = []
            for pm in pms:
                # if pr.show_keymap_names and km_name != pm.km_name:
                #     km_name = pm.km_name
                #     link = PMLink.add()
                #     link.label = km_name
                #     idx += 1

                if pm.name in folders:
                    link = PMLink.add()
                    link.group = km
                    link.is_folder = True
                    link.pm_name = pm.name
                    if pm.name == apm_name and (
                            not sel_link or not sel_folder):
                        aidx = idx
                    idx += 1
                    path.append(pm.name)
                    idx, aidx = add_children(
                        folders[pm.name], km, path, idx, aidx)
                    path.pop()

                # elif pm.name not in files:
                else:
                    link = PMLink.add()
                    link.group = km
                    link.pm_name = pm.name
                    if pm.name == apm_name and (
                            not sel_link or not sel_folder):
                        aidx = idx
                    idx += 1

            pm_links = {}
            for link in tpr.links:
                if link.label:
                    continue
                if link.pm_name not in pm_links:
                    pm_links[link.pm_name] = []
                pm_links[link.pm_name].append(link)

            links_to_remove = set()
            fixed_links = set()
            for pm_name, links in pm_links.items():
                if len(links) == 1:
                    continue
                links.sort(key=lambda link: len(link.path), reverse=True)
                can_be_removed = False
                for link in links:
                    if len(link.path) == 0:
                        if can_be_removed and link.pm_name not in fixed_links:
                            links_to_remove.add(link.name)
                            DBG_TREE and logi("REMOVE", link.pm_name)
                    else:
                        if not can_be_removed and \
                                link.name not in links_to_remove and \
                                link.path[0] != pm_name:
                            fixed_links.add(link.path[0])
                            DBG_TREE and logi("FIXED", link.path[0])
                            can_be_removed = True

            prev_link_will_be_removed = False
            for link in tpr.links:
                if link.label:
                    prev_link_will_be_removed = False
                    continue
                if link.path:
                    if prev_link_will_be_removed:
                        links_to_remove.add(link.name)
                else:
                    prev_link_will_be_removed = link.name in links_to_remove

            for link in links_to_remove:
                PME_UL_pm_tree.expanded_folders.discard(
                    tpr.links[link].fullpath())
                tpr.links.remove(tpr.links.find(link))

            if pr.show_keymap_names:
                links_to_remove.clear()
                prev_link = None
                for link in tpr.links:
                    if link.label and prev_link and prev_link.label:
                        links_to_remove.add(prev_link.name)
                    prev_link = link

                if prev_link and prev_link.label:
                    links_to_remove.add(prev_link.name)

                for link in links_to_remove:
                    tpr.links.remove(tpr.links.find(link))

            aidx = -1
            for i, link in enumerate(tpr.links):
                if link.pm_name == apm_name:
                    aidx = i
                    break

            tpr["links_idx"] = aidx
            if len(tpr.links):
                sel_link = tpr.links[tpr.links_idx]
                if sel_link.pm_name:
                    pm = pr.selected_pm
                    if pm.km_name in PME_UL_pm_tree.collapsed_km_names:
                        PME_UL_pm_tree.collapsed_km_names.remove(pm.km_name)

    def draw_item(
            self, context, layout, data, item,
            icon, active_data, active_propname, index):
        pr = prefs()

        # if pr.show_hotkeys and item.pm_name:
        #     layout = layout.split(0.6, True)
        layout = layout.row(True)
        lh.lt(layout)

        if item.pm_name:
            # if item.folder:
            #     lh.label("", icon='BLANK1')
            pm = pr.pie_menus[item.pm_name]

            # WM_UL_pm_list.draw_item(
            #     self, context, lh.layout, data, pm, icon,
            #     active_data, active_propname, index)

            # lh.row(layout, alignment='LEFT')

            lh.prop(
                pm, "enabled", "", ICON_ON if pm.enabled else ICON_OFF,
                emboss=False)

            for i in range(0, len(item.path)):
                lh.label("", icon='BLANK1')

            lh.label("", pm.ed.icon)

            if item.is_folder:
                icon = 'TRIA_DOWN' \
                    if item.fullpath() in PME_UL_pm_tree.expanded_folders \
                    else 'TRIA_RIGHT'
                lh.operator(
                    PME_OT_tree_folder_toggle.bl_idname, "",
                    icon, emboss=False,
                    folder=item.fullpath(),
                    idx=index)

            hk = pm.to_hotkey()
            if pr.show_names or not pr.show_hotkeys or not hk:
                lh.prop(pm, "label", "", emboss=False)

            if pr.show_hotkeys and hk:
                if pr.show_names:
                    lh.row(layout, alignment='RIGHT')

                lh.label(hk)

        else:
            lh.row()
            # lh.layout.active = False
            lh.layout.scale_y = 0.95
            icon = 'TRIA_RIGHT_BAR' \
                if item.label in PME_UL_pm_tree.collapsed_km_names else \
                'TRIA_DOWN_BAR'
            lh.operator(
                PME_OT_tree_kmname_toggle.bl_idname, item.label,
                icon, km_name=item.label, idx=index, all=False)
            # lh.label()
            icon = 'TRIA_LEFT_BAR' \
                if item.label in PME_UL_pm_tree.collapsed_km_names else \
                'TRIA_DOWN_BAR'
            lh.operator(
                PME_OT_tree_kmname_toggle.bl_idname, "",
                icon, km_name=item.label, idx=index,
                all=True)

    def draw_filter(self, context, layout):
        pr = prefs()

        row = layout.row(True)
        row.prop(
            pr, "show_names", icon='SYNTAX_OFF', toggle=True)
        row.prop(
            pr, "show_hotkeys", icon='FONTPREVIEW', toggle=True)
        row.prop(
            pr, "show_keymap_names", icon='SPLITSCREEN', toggle=True)

    def filter_items(self, context, data, propname):
        pr = prefs()

        links = getattr(data, propname)
        filtered = [self.bitflag_filter_item] * len(links)

        cur_kmname = None
        for idx, link in enumerate(links):
            pm = None
            if link.path:
                pm = pr.pie_menus[link.path[0]]
            elif link.pm_name:
                pm = pr.pie_menus[link.pm_name]

            if link.label and pr.show_keymap_names:
                cur_kmname = link.label

            if pr.show_keymap_names and pm and \
                    cur_kmname in pm.km_name and \
                    cur_kmname in PME_UL_pm_tree.collapsed_km_names or \
                    link.path and \
                    PME_UL_pm_tree.link_is_collapsed(link):
                filtered[idx] = 0

        return filtered, []


class PME_OT_tree_folder_toggle(bpy.types.Operator):
    bl_idname = "pme.tree_folder_toggle"
    bl_label = ""
    bl_description = "Expand or collapse"
    bl_options = {'INTERNAL'}

    folder = bpy.props.StringProperty()
    idx = bpy.props.IntProperty()

    def execute(self, context):
        temp_prefs().links_idx = self.idx
        if self.folder:
            if self.folder in PME_UL_pm_tree.expanded_folders:
                PME_UL_pm_tree.expanded_folders.remove(self.folder)
            else:
                PME_UL_pm_tree.expanded_folders.add(self.folder)
        return {'FINISHED'}


class PME_OT_tree_folder_toggle_all(bpy.types.Operator):
    bl_idname = "pme.tree_folder_toggle_all"
    bl_label = ""
    bl_description = "Expand or collapse all menus"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        if PME_UL_pm_tree.expanded_folders:
            PME_UL_pm_tree.expanded_folders.clear()
        else:
            for link in temp_prefs().links:
                if link.is_folder:
                    PME_UL_pm_tree.expanded_folders.add(link.fullpath())
        return {'FINISHED'}


class PME_OT_tree_kmname_toggle(bpy.types.Operator):
    bl_idname = "pme.tree_kmname_toggle"
    bl_label = ""
    bl_description = "Expand or collapse keymap names"
    bl_options = {'INTERNAL'}

    km_name = bpy.props.StringProperty()
    idx = bpy.props.IntProperty()
    all = bpy.props.BoolProperty()

    def execute(self, context):
        tpr = temp_prefs()

        if self.idx != -1:
            tpr.links_idx = self.idx

        if self.all:
            add = len(PME_UL_pm_tree.collapsed_km_names) == 0
            for link in tpr.links:
                if not link.label:
                    continue
                if link.label == self.km_name:
                    continue
                if self.km_name:
                    PME_UL_pm_tree.collapsed_km_names.add(link.label)
                elif add:
                    PME_UL_pm_tree.collapsed_km_names.add(link.label)
                else:
                    PME_UL_pm_tree.collapsed_km_names.discard(link.label)

            if self.km_name and \
                    self.km_name in PME_UL_pm_tree.collapsed_km_names:
                PME_UL_pm_tree.collapsed_km_names.remove(self.km_name)

        else:
            if self.km_name in PME_UL_pm_tree.collapsed_km_names:
                PME_UL_pm_tree.collapsed_km_names.remove(self.km_name)
            else:
                PME_UL_pm_tree.collapsed_km_names.add(self.km_name)

        return {'FINISHED'}


class PMIItem(bpy.types.PropertyGroup):
    expandable_props = {}

    mode = EnumProperty(items=MODE_ITEMS, description="Type of the item")
    text = StringProperty(maxlen=1024)
    icon = StringProperty(description="Icon")

    def get_pmi_label(self):
        return self.name

    def set_pmi_label(self, value):
        if self.name == value:
            return
        pm = prefs().selected_pm
        if pm.mode != 'PANEL':
            return

        for pmi in pm.pmis:
            if pmi == self:
                self.name = value
                pm.update_panel_group()
                break

    label = StringProperty(
        description="Label", get=get_pmi_label, set=set_pmi_label)

    @property
    def rm_class(self):
        value = self.text.replace("@", "")
        return get_pme_menu_class(value)

    def from_dict(self, value):
        pass

    def to_dict(self):
        return {k: self[k] for k in self.keys()}

    def parse(self, default_icon='NONE'):
        icon, icon_only, hidden = self.extract_flags()
        oicon = icon
        text = self.name

        if icon_only:
            text = ""
        if hidden:
            icon = 'NONE' if not icon or not icon_only else 'BLANK1'
            if text:
                text = ""
        elif not icon:
            icon = default_icon

        if not hidden:
            if self.mode == 'PROP':
                bl_prop = bp.get(
                    self.prop if hasattr(self, "prop") else self.text)
                if bl_prop:
                    if bl_prop.type in {'STRING', 'ENUM', 'POINTER'}:
                        text = ""
                    if bl_prop.type in {'FLOAT', 'INT', 'BOOLEAN'} and len(
                            bl_prop.default_array) > 1:
                        text = ""

            if icon[0] != "@" and icon not in AVAILABLE_ICONS:
                icon = default_icon

        return text, icon, oicon, icon_only, hidden

    def extract_flags(self):
        icon = self.icon
        hidden = False
        icon_only = False
        while icon:
            if icon[0] == "!":
                hidden = True
            elif icon[0] == "#":
                icon_only = True
            else:
                break
            icon = icon[1:]
        return icon, icon_only, hidden

    def parse_icon(self, default_icon='NONE'):
        icon = self.extract_flags()[0]
        if not icon:
            return default_icon

        if icon[0] != "@" and icon not in AVAILABLE_ICONS:
            return default_icon

        return icon

    def parse_menu_data(self):
        data = self.text
        if not data:
            return False, ""

        mouse_over = data[0] == "@"
        if mouse_over:
            data = data[1:]

        return mouse_over, data

    def copy_item(self):
        PMEPreferences.pmi_clipboard = (
            self.name, self.icon, self.mode, self.text)

    def paste_item(self):
        pr = prefs()
        pm = pr.selected_pm

        self.name, self.icon, self.mode, self.text = pr.pmi_clipboard

        if pm.mode != 'DIALOG':
            self.icon, _, _ = self.extract_flags()

    def is_expandable_prop(self):
        if self.mode != 'PROP':
            return False

        prop = self.text
        if prop in self.expandable_props:
            return self.expandable_props[prop]

        value = None
        try:
            value = eval(prop)
        except:
            return False

        self.expandable_props[prop] = not isinstance(value, bool)

        return self.expandable_props[prop]


class PMItem(bpy.types.PropertyGroup):
    poll_methods = {}

    @staticmethod
    def _parse_keymap(km_name, exists=True):
        names = []
        keymaps = bpy.context.window_manager.keyconfigs.user.keymaps
        for name in km_name.split(","):
            name = name.strip()
            if not name:
                continue

            name_in_keymaps = name in keymaps
            if exists and not name_in_keymaps or \
                    not exists and name_in_keymaps:
                continue

            names.append(name)

        if exists and not names:
            names.append("Window")

        return names

    def parse_keymap(self, exists=True):
        return PMItem._parse_keymap(self.km_name, exists)

    def get_pm_km_name(self):
        if "km_name" not in self:
            self["km_name"] = "Window"
        return self["km_name"]

    def set_pm_km_name(self, value):
        if not value:
            value = "Window"
        else:
            value = ", ".join(PMItem._parse_keymap(value))

        if "km_name" not in self or self["km_name"] != value:
            if "km_name" in self:
                self.unregister_hotkey()

            self["km_name"] = value
            self.register_hotkey()

        PME_UL_pm_tree.update_tree()

    km_name = StringProperty(
        default="Window", description="Keymap names",
        get=get_pm_km_name, set=set_pm_km_name)

    def get_pm_name(self):
        return self.name

    def set_pm_name(self, value):
        pr = prefs()
        pme = bpy.context.window_manager.pme

        value = value.replace("@", "")

        if value == self.name:
            return

        if value:
            if value in pr.pie_menus:
                value = pr.unique_pm_name(value)

            if self.mode == 'PANEL':
                rename_panel_group(self.name, value)

            elif self.mode == 'MACRO':
                # rename_macro(self.name, value)
                remove_macro(self)

            for link in pme.links:
                if link.pm_name == self.name:
                    link.pm_name = value

            if self.mode == 'RMENU' and self.name in pme_menu_classes:
                del pme_menu_classes[self.name]
                get_pme_menu_class(value)

            for pm in pr.pie_menus:
                if pm == self:
                    continue

                for pmi in pm.pmis:
                    if pmi.mode == 'MENU':
                        mouse_over, menu_name = pmi.parse_menu_data()
                        if menu_name == self.name:
                            pmi.text = "@" + value if mouse_over else value

            if self.name in kmis_map:
                if kmis_map[self.name]:
                    self.unregister_hotkey()
                else:
                    kmis_map[value] = kmis_map[self.name]
                    del kmis_map[self.name]

            if self.name in PME_UL_pm_tree.expanded_folders:
                PME_UL_pm_tree.expanded_folders.remove(self.name)
                PME_UL_pm_tree.expanded_folders.add(value)

            if self.name in pr.old_pms:
                pr.old_pms.remove(self.name)
                pr.old_pms.add(value)

            for link in temp_prefs().links:
                if link.pm_name == self.name:
                    link.pm_name = value
                for i in range(0, len(link.path)):
                    if link.path[i] == self.name:
                        link.path[i] = value

            self.name = value

            if self.mode == 'MACRO':
                add_macro(self)

            if self.name not in kmis_map:
                self.register_hotkey()

            PME_UL_pm_tree.update_tree()

    label = StringProperty(
        get=get_pm_name, set=set_pm_name, description="Menu name")

    pmis = CollectionProperty(type=PMIItem)
    mode = EnumProperty(items=PM_ITEMS)

    def update_keymap_item(self, context):
        pr = prefs()
        kmis = kmis_map[self.name]

        if kmis:
            for k in kmis.keys():
                kmi = kmis[k]

                for map_type in MAP_TYPES:
                    try:
                        kmi.type = self.key
                        break
                    except TypeError:
                        kmi.map_type = map_type

                kmi.ctrl = self.ctrl
                kmi.shift = self.shift
                kmi.alt = self.alt
                kmi.oskey = self.oskey
                kmi.key_modifier = self.key_mod
                kmi.value = \
                    'DOUBLE_CLICK' if self.open_mode == 'DOUBLE_CLICK' \
                    else 'PRESS'

                if self.key == 'NONE' or not self.enabled:
                    if pr.kh.available():
                        pr.kh.keymap(k)
                        pr.kh.remove(kmi)

            if self.key == 'NONE' or not self.enabled:
                kmis_map[self.name] = None
        else:
            self.register_hotkey()

    open_mode = EnumProperty(
        name="Open Mode",
        items=OPEN_MODE_ITEMS,
        update=update_keymap_item)
    key = EnumProperty(
        items=keymap_helper.key_items,
        description="Key pressed", update=update_keymap_item)
    ctrl = BoolProperty(
        description="Ctrl key pressed", update=update_keymap_item)
    shift = BoolProperty(
        description="Shift key pressed", update=update_keymap_item)
    alt = BoolProperty(
        description="Alt key pressed", update=update_keymap_item)
    oskey = BoolProperty(
        description="Operating system key pressed", update=update_keymap_item)

    def get_pm_key_mod(self):
        return self["key_mod"] if "key_mod" in self else 0

    def set_pm_key_mod(self, value):
        pr = prefs()
        prev_value = self.key_mod
        self["key_mod"] = value
        value = self.key_mod

        if prev_value == value or not self.enabled:
            return

        kms = self.parse_keymap()
        if prev_value != 'NONE' and prev_value in MOUSE_BUTTONS:
            for km in kms:
                remove_mouse_button(prev_value, pr.kh, km)

        if value != 'NONE' and value in MOUSE_BUTTONS:
            for km in kms:
                add_mouse_button(value, pr.kh, km)

    key_mod = EnumProperty(
        items=keymap_helper.key_items,
        description="Regular key pressed as a modifier",
        get=get_pm_key_mod, set=set_pm_key_mod)

    def get_pm_enabled(self):
        if "enabled" not in self:
            self["enabled"] = True
        return self["enabled"]

    def set_pm_enabled(self, value):
        if "enabled" in self and self["enabled"] == value:
            return

        self["enabled"] = value

        if self.mode == 'PANEL':
            if self.enabled:
                for i, pmi in enumerate(self.pmis):
                    add_panel(
                        self.name, i, pmi.text, pmi.name,
                        self.panel_space, self.panel_region,
                        self.panel_context, self.panel_category,
                        draw_pme_panel, poll_pme_panel)
            else:
                remove_panel_group(self.name)

        elif self.mode == 'HPANEL':
            for pmi in self.pmis:
                if self.enabled:
                    hide_panel(pmi.text)
                else:
                    unhide_panel(pmi.text)

        elif self.mode == 'MACRO':
            if self.enabled:
                add_macro(self)
            else:
                remove_macro(self)

        if self.ed.has_hotkey:
            self.update_keymap_item(bpy.context)

            if self.key_mod in MOUSE_BUTTONS:
                kms = self.parse_keymap()
                for km in kms:
                    if self.enabled:
                        pass
                        # add_mouse_button(pm.key_mod, kh, km)
                    else:
                        remove_mouse_button(self.key_mod, prefs().kh, km)

    enabled = BoolProperty(
        description="Enable or disable the menu",
        default=True,
        get=get_pm_enabled, set=set_pm_enabled)

    def update_poll_cmd(self, context):
        if self.poll_cmd == DEFAULT_POLL:
            self.poll_methods.pop(self.name, None)
        else:
            exec_locals = pme.context.gen_locals()
            try:
                exec(
                    "def poll(cls, context):" + self.poll_cmd,
                    pme.context.globals, exec_locals)
                self.poll_methods[self.name] = exec_locals["poll"]
            except:
                self.poll_methods[self.name] = None

    poll_cmd = StringProperty(
        description=(
            "Poll method\nTest if the item can be called/displayed or not"),
        default=DEFAULT_POLL, maxlen=1024, update=update_poll_cmd)
    data = StringProperty(maxlen=1024)

    def update_panel_group(self):
        remove_panel_group(self.name)

        for i, pmi in enumerate(self.pmis):
            add_panel(
                self.name, i, pmi.text, pmi.name,
                self.panel_space, self.panel_region,
                self.panel_context, self.panel_category,
                draw_pme_panel, poll_pme_panel)

    def get_panel_context(self):
        prop = pp.parse(self.data)
        for item in panel_context_items(self, bpy.context):
            if item[0] == prop.pg_context:
                return item[4]
        return 0

    def set_panel_context(self, value):
        value = panel_context_items(self, bpy.context)[value][0]
        prop = pp.parse(self.data)
        if prop.pg_context == value:
            return
        self.data = pp.encode(self.data, "pg_context", value)
        self.update_panel_group()

    panel_context = EnumProperty(
        items=panel_context_items,
        name="Context",
        description="Panel context",
        get=get_panel_context, set=set_panel_context)

    def get_panel_category(self):
        prop = pp.parse(self.data)
        return prop.pg_category

    def set_panel_category(self, value):
        prop = pp.parse(self.data)
        if prop.pg_category == value:
            return
        self.data = pp.encode(self.data, "pg_category", value)
        self.update_panel_group()

    panel_category = StringProperty(
        default="My Category", description="Panel category",
        get=get_panel_category, set=set_panel_category)

    def get_panel_region(self):
        prop = pp.parse(self.data)
        for item in REGION_ITEMS:
            if item[0] == prop.pg_region:
                return item[4]
        return 0

    def set_panel_region(self, value):
        value = REGION_ITEMS[value][0]
        prop = pp.parse(self.data)
        if prop.pg_region == value:
            return
        self.data = pp.encode(self.data, "pg_region", value)
        self.update_panel_group()

    panel_region = EnumProperty(
        items=REGION_ITEMS,
        name="Region",
        description="Panel region",
        get=get_panel_region, set=set_panel_region)

    def get_panel_space(self):
        prop = pp.parse(self.data)
        for item in SPACE_ITEMS:
            if item[0] == prop.pg_space:
                return item[4]
        return 0

    def set_panel_space(self, value):
        value = SPACE_ITEMS[value][0]
        prop = pp.parse(self.data)
        if prop.pg_space == value:
            return
        self.data = pp.encode(self.data, "pg_space", value)
        self.update_panel_group()

    panel_space = EnumProperty(
        items=SPACE_ITEMS,
        name="Space",
        description="Panel space",
        get=get_panel_space, set=set_panel_space)

    pm_radius = IntProperty(
        subtype='PIXEL',
        description="Radius of the pie menu (-1 - use default value)",
        get=lambda s: s.get_data("pm_radius"),
        set=lambda s, v: s.set_data("pm_radius", v),
        default=-1, step=10, min=-1, max=1000)
    pm_threshold = IntProperty(
        subtype='PIXEL',
        description=(
            "Distance from center needed "
            "before a selection can be made(-1 - use default value)"),
        get=lambda s: s.get_data("pm_threshold"),
        set=lambda s, v: s.set_data("pm_threshold", v),
        default=-1, step=10, min=-1, max=1000)
    pm_confirm = IntProperty(
        subtype='PIXEL',
        description=(
            "Distance threshold after which selection is made "
            "(-1 - use default value)"),
        get=lambda s: s.get_data("pm_confirm"),
        set=lambda s, v: s.set_data("pm_confirm", v),
        default=-1, step=10, min=-1, max=1000)
    pm_flick = BoolProperty(
        name="Confirm on Release",
        description="Confirm selection when releasing the hotkey",
        get=lambda s: s.get_data("pm_flick"),
        set=lambda s, v: s.set_data("pm_flick", v))
    pd_box = BoolProperty(
        name="Use Frame", description="Use a frame",
        get=lambda s: s.get_data("pd_box"),
        set=lambda s, v: s.set_data("pd_box", v))
    pd_auto_close = BoolProperty(
        name="Auto Close on Mouse Out", description="Auto close on mouse out",
        get=lambda s: s.get_data("pd_auto_close"),
        set=lambda s, v: s.set_data("pd_auto_close", v))
    pd_expand = BoolProperty(
        name="Expand Sub Popup Dialogs",
        description=(
            "Expand all sub popup dialogs "
            "instead of using them as a button"),
        get=lambda s: s.get_data("pd_expand"),
        set=lambda s, v: s.set_data("pd_expand", v))
    pd_panel = EnumProperty(
        name="Dialog Mode", description="Popup dialog mode",
        items=PD_MODE_ITEMS,
        get=lambda s: s.get_data("pd_panel"),
        set=lambda s, v: s.set_data("pd_panel", v))
    pd_width = IntProperty(
        name="Width", description="Width of the popup",
        get=lambda s: s.get_data("pd_width"),
        set=lambda s, v: s.set_data("pd_width", v),
        step=50, min=150, max=2000)
    rm_title = BoolProperty(
        name="Show Title", description="Show title",
        get=lambda s: s.get_data("rm_title"),
        set=lambda s, v: s.set_data("rm_title", v))
    s_undo = BoolProperty(
        name="Undo Previous Command", description="Undo previous command",
        get=lambda s: s.get_data("s_undo"),
        set=lambda s, v: s.set_data("s_undo", v))

    def poll(self, cls=None, context=None):
        if self.poll_cmd == DEFAULT_POLL:
            return True

        if self.name not in self.poll_methods:
            self.update_poll_cmd(bpy.context)

        poll_method = self.poll_methods[self.name]
        return poll_method is None or poll_method(cls, context)

    @property
    def is_new(self):
        return self.name not in prefs().old_pms

    def register_hotkey(self, km_names=None):
        pr = prefs()
        kmis_map[self.name] = None

        if self.key == 'NONE' or not self.enabled:
            return

        if pr.kh.available():
            if km_names is None:
                km_names = self.parse_keymap()
            for km_name in km_names:
                pr.kh.keymap(km_name)
                kmi = pr.kh.operator(
                    WM_OT_pme_user_pie_menu_call,
                    None,  # hotkey
                    self.key, self.ctrl, self.shift, self.alt, self.oskey,
                    'NONE' if self.key_mod in MOUSE_BUTTONS else self.key_mod
                )
                kmi.properties.pie_menu_name = self.name
                kmi.properties.invoke_mode = 'HOTKEY'
                kmi.properties.keymap = km_name

                kmi.value = \
                    'DOUBLE_CLICK' if self.open_mode == 'DOUBLE_CLICK' \
                    else 'PRESS'

                if kmis_map[self.name]:
                    kmis_map[self.name][km_name] = kmi
                else:
                    kmis_map[self.name] = {km_name: kmi}

                if self.key_mod in MOUSE_BUTTONS:
                    add_mouse_button(self.key_mod, pr.kh, km_name)

    def unregister_hotkey(self):
        pr = prefs()
        if pr.kh.available() and self.name in kmis_map and kmis_map[self.name]:
            for k in kmis_map[self.name].keys():
                pr.kh.keymap(k)
                pr.kh.remove(kmis_map[self.name][k])

                if self.key_mod in MOUSE_BUTTONS:
                    remove_mouse_button(self.key_mod, pr.kh, k)

        if self.name in kmis_map:
            del kmis_map[self.name]

    def filter_by_mode(self, pr):
        return self.mode in pr.mode_filter
        # if self.mode == 'PMENU':
        #     return pr.show_pm
        # if self.mode == 'RMENU':
        #     return pr.show_rm
        # if self.mode == 'DIALOG':
        #     return pr.show_pd
        # if self.mode == 'SCRIPT':
        #     return pr.show_scripts
        # if self.mode == 'STICKY':
        #     return pr.show_sticky
        # if self.mode == 'PANEL':
        #     return pr.show_pg
        # if self.mode == 'HPANEL':
        #     return pr.show_hpg
        # if self.mode == 'MACRO':
        #     return pr.show_macro

    def filter(self, pr):
        return self.filter_by_mode(pr) and (
            not pr.show_only_new_pms or self.is_new)

    def from_dict(self, value):
        pass

    def to_dict(self):
        d = {}
        return d

    def to_hotkey(self, use_key_names=True):
        return keymap_helper.to_hotkey(
            self.key, self.ctrl, self.shift, self.alt, self.oskey,
            self.key_mod, use_key_names=use_key_names)

    def get_data(self, key):
        value = getattr(pp.parse(self.data), key)
        # prop = pp.get(key)
        # if prop.ptype == 'BOOL':
        #     value = value != ""
        # elif prop.ptype == 'INT':
        #     value = int(value) if value else 0

        return value

    def set_data(self, key, value):
        # prop = pp.get(key)
        # if prop.ptype == 'BOOL':
        #     value = "1" if value else ""
        # elif prop.ptype == 'INT':
        #     value = str(value)

        self.data = pp.encode(self.data, key, value)

    @property
    def ed(self):
        return EDITORS[self.mode]

    def __str__(self):
        return "[%s][%s][%s] %s" % (
            "V" if self.enabled else " ",
            self.mode, self.to_hotkey(), self.label
        )


class PMIData(bpy.types.PropertyGroup):
    _kmi = None

    @property
    def kmi(self):
        pr = prefs()
        if not PMIData._kmi:
            pr.kh.keymap()
            PMIData._kmi = pr.kh.operator(PME_OT_none)
            PMIData._kmi.active = False

        return PMIData._kmi

    def check_pmi_errors(self, context):
        self.info("")

        pr = prefs()
        pm = pr.selected_pm
        if self.mode == 'COMMAND':
            self.sname = ""
            mo = re_operator.search(self.cmd)
            if mo:
                self.sname = gen_op_name(mo, True)
            else:
                mo = re_prop.search(self.cmd)
                if mo:
                    self.sname, icon = gen_prop_name(mo, False, True)

            if self.cmd:
                try:
                    compile(self.cmd, '<string>', 'exec')
                except:
                    self.info("Invalid syntax")

            if pm.mode == 'STICKY':
                PME_OT_sticky_key_edit.parse_prop_value(self.cmd)

        elif self.mode == 'PROP':
            self.sname = ""
            mo = re_prop_set.search(self.prop)
            if mo:
                self.sname, icon = gen_prop_name(mo, True, True)
                if icon and icon != 'NONE':
                    pmi = pm.pmis[pme.context.edit_item_idx]
                    _, icon_only, hidden = pmi.extract_flags()
                    if icon_only:
                        icon = "#" + icon
                    if hidden:
                        icon = "!" + icon
                    pmi.icon = icon

        elif self.mode == 'MENU':
            self.sname = self.menu
            pr = prefs()
            if not self.menu:
                self.info("Select the item")
            elif self.menu not in pr.pie_menus:
                self.info("'%s' was not found" % self.menu)
            # elif not pr.pie_menus[self.menu].ed.sub_item:
            #     self.info("'%s' is not supported here" % self.menu)

        elif self.mode == 'HOTKEY':
            self.sname = keymap_helper.to_hotkey(
                self.key, self.ctrl, self.shift, self.alt,
                self.oskey, self.key_mod)
            if self.key == 'NONE':
                self.info("Hotkey is not specified")

        elif self.mode == 'CUSTOM':
            self.sname = ""
            pm = pr.selected_pm

            if self.custom:
                try:
                    compile(self.custom, '<string>', 'exec')
                except:
                    self.info("Invalid syntax")

    def update_data(self, context):
        pr = prefs()
        self.check_pmi_errors(context)

        if self.mode == 'COMMAND' and pr.use_cmd_editor:
            op_idname, args, pos_args = operator_utils.find_operator(self.cmd)

            self.kmi.idname = ""
            self.cmd_ctx = 'INVOKE_DEFAULT'
            self.cmd_undo = False

            if not op_idname:
                return
            else:
                mod, _, op = op_idname.partition(".")
                if not hasattr(
                        bpy.types,
                        getattr(getattr(bpy.ops, mod), op).idname()):
                    return

            self.kmi.idname = op_idname

            has_exec_ctx = False
            has_undo = False
            for i, arg in enumerate(pos_args):
                if i > 2:
                    break
                try:
                    value = eval(arg)
                except:
                    continue
                try:
                    if isinstance(value, str):
                        self.cmd_ctx = value
                        has_exec_ctx = True
                        continue
                except:
                    self.cmd_ctx = 'INVOKE_DEFAULT'
                    continue

                if isinstance(value, bool):
                    has_undo = True
                    self.cmd_undo = value

            if has_undo and not has_exec_ctx:
                self.cmd_ctx = 'EXEC_DEFAULT'

            for k in self.kmi.properties.keys():
                del self.kmi.properties[k]

            operator_utils.apply_properties(self.kmi.properties, args)

    mode = EnumProperty(
        items=EMODE_ITEMS, description="Type of the item",
        update=check_pmi_errors)
    cmd = StringProperty(
        description="Python code", maxlen=1024, update=update_data)
    cmd_ctx = EnumProperty(
        items=OP_CTX_ITEMS,
        name="Execution Context",
        description="Execution context")
    cmd_undo = BoolProperty(
        name="Undo Flag",
        description="'Undo' positional argument")
    custom = StringProperty(
        description="Python code", maxlen=1024, update=update_data)
    prop = StringProperty(
        description="Property", update=update_data)
    menu = StringProperty(
        description="Menu's name", update=update_data)
    xmenu = BoolProperty(
        description="Open menu on mouse over")
    icon = StringProperty(description="Name")
    name = StringProperty(description="Name")
    sname = StringProperty(description="Suggested name")
    key = EnumProperty(
        items=keymap_helper.key_items, description="Key pressed",
        update=update_data)
    ctrl = BoolProperty(
        description="Ctrl key pressed")
    shift = BoolProperty(
        description="Shift key pressed")
    alt = BoolProperty(
        description="Alt key pressed")
    oskey = BoolProperty(
        description="Operating system key pressed")
    key_mod = EnumProperty(
        items=keymap_helper.key_items,
        description="Regular key pressed as a modifier")

    msg = StringProperty(description="Name")

    def info(self, text):
        self.msg = text

    def has_messages(self):
        return self.msg != ""

    def extract_flags(self):
        return PMIItem.extract_flags(self)

    def parse_icon(self, default_icon='NONE'):
        return PMIItem.parse_icon(self, default_icon)


class Overlay(bpy.types.PropertyGroup):
    overlay = BoolProperty(
        name="Display Stack Key Command",
        description=(
            "Display the name of the last command on screen "
            "for stack keys with 2+ commands"),
        default=True)
    size = IntProperty(
        name="Font Size", description="Font size",
        default=24, min=10, max=50, options={'SKIP_SAVE'})
    color = FloatVectorProperty(
        name="Color", description="Color",
        default=(1, 1, 1, 1), subtype='COLOR', size=4, min=0, max=1)
    alignment = EnumProperty(
        name="Alignment",
        description="Alignment",
        items=(
            ('TOP', "Top", ""),
            ('TOP_LEFT', "Top Left", ""),
            ('TOP_RIGHT', "Top Right", ""),
            ('BOTTOM', "Bottom", ""),
            ('BOTTOM_LEFT', "Bottom Left", ""),
            ('BOTTOM_RIGHT', "Bottom Right", ""),
        ),
        default='TOP')
    duration = FloatProperty(
        name="Duration", subtype='TIME', min=1, max=10, default=2, step=10)
    offset_x = IntProperty(
        name="Offset X", description="Offset from area edges",
        subtype='PIXEL', default=10, min=0)
    offset_y = IntProperty(
        name="Offset Y", description="Offset from area edges",
        subtype='PIXEL', default=10, min=0)
    shadow = BoolProperty(
        name="Use Shadow", description="Use shadow", default=True)

    def draw(self, layout):
        if not self.overlay:
            layout.prop(self, "overlay", toggle=True)
        else:
            layout = layout.column(True)
            layout.prop(self, "overlay", toggle=True)

            row = layout.split(0.5, True)
            row1 = row.row(True)
            row1.prop(self, "color", "")
            row1.prop(self, "shadow", "", icon='META_BALL')

            row.prop(self, "size")
            row.prop(self, "duration")

            row = layout.split(0.5, True)
            row.prop(self, "alignment", "")
            row.prop(self, "offset_x")
            row.prop(self, "offset_y")


class PieMenuPrefs:
    def __init__(self):
        self.num_saves = 0
        self.lock = False
        self.radius = 80
        self.confirm = 0
        self.threshold = 12

    def save(self):
        self.num_saves += 1
        # logi("SAVE", self.num_saves, self.lock)
        if not self.lock:
            view_prefs = bpy.context.user_preferences.view
            if view_prefs.pie_menu_radius > 0:
                self.radius = view_prefs.pie_menu_radius
            self.confirm = view_prefs.pie_menu_confirm
            self.threshold = view_prefs.pie_menu_threshold
            self.lock = True

    def restore(self):
        self.num_saves -= 1
        # logi("RESTORE", self.num_saves)
        if self.lock and self.num_saves == 0:
            view_prefs = bpy.context.user_preferences.view
            view_prefs.pie_menu_radius = self.radius
            view_prefs.pie_menu_confirm = self.confirm
            view_prefs.pie_menu_threshold = self.threshold
            self.lock = False


class TreeView:

    def expand_km(self, name):
        if name in PME_UL_pm_tree.collapsed_km_names:
            PME_UL_pm_tree.collapsed_km_names.remove(name)

    def lock(self):
        PME_UL_pm_tree.locked = True

    def unlock(self):
        PME_UL_pm_tree.locked = False

    def update(self):
        PME_UL_pm_tree.update_tree()


class PMEPreferences(bpy.types.AddonPreferences):
    bl_idname = ADDON_ID

    _mode = 'ADDON'
    mode_history = []
    unregistered_pms = []
    old_pms = set()
    missing_kms = {}
    pie_menu_prefs = PieMenuPrefs()
    tree = TreeView()
    pmi_clipboard = None
    pdr_clipboard = None
    rmc_clipboard = None

    pie_menus = CollectionProperty(type=PMItem)

    def update_pie_menu_idx(self, context):
        self.pmi_data.info("")
        temp_prefs().hidden_panels_idx = 0

    active_pie_menu_idx = IntProperty(update=update_pie_menu_idx)

    overlay = PointerProperty(type=Overlay)
    list_size = IntProperty(
        name="List Width", description="Width of the list",
        default=40, min=20, max=80, subtype='PERCENTAGE'
    )

    def update_interactive_panels(self, context=None):
        if PME_OT_interactive_panels_toggle.active == self.interactive_panels:
            return

        PME_OT_interactive_panels_toggle.active = self.interactive_panels

        for tp in bl_panel_types():
            if tp.bl_space_type == 'USER_PREFERENCES':
                continue
            if self.interactive_panels:
                tp.append(PME_OT_interactive_panels_toggle._draw)
            else:
                tp.remove(PME_OT_interactive_panels_toggle._draw)

        tag_redraw(True)

    interactive_panels = BoolProperty(
        name="Interactive Panels",
        description="Interactive panels",
        update=update_interactive_panels)

    icon_filter = StringProperty(
        description="Filter", options={'TEXTEDIT_UPDATE'})
    hotkey = PointerProperty(type=keymap_helper.Hotkey)
    hold_time = IntProperty(
        name="Hold Timeout", description="Hold timeout (ms)",
        default=200, min=50, max=1000, step=10)
    tab = EnumProperty(
        items=(
            ('EDITOR', "Editor", ""),
            ('SETTINGS', "Settings", ""),
        ),
        options={'HIDDEN'})
    show_names = BoolProperty(
        default=True, description="Show names")
    show_hotkeys = BoolProperty(
        default=True, description="Show hotkeys")

    def update_tree(self, context=None):
        self.tree.update()

    show_keymap_names = BoolProperty(
        name="Keymap Names",
        default=False, description="Show keymap names",
        update=update_tree)

    show_custom_icons = BoolProperty(
        default=False, description="Show custom icons")
    show_advanced_settings = BoolProperty(
        default=False, description="Advanced settings")
    show_list = BoolProperty(
        default=True, description="Show the list of pie menus")

    use_filter = BoolProperty(
        description="Use filter", update=update_tree)
    mode_filter = EnumProperty(
        items=PM_ITEMS_M, default=PM_ITEMS_M_DEFAULT,
        description="Show icons",
        options={'ENUM_FLAG'},
        update=update_tree
    )
    show_only_new_pms = BoolProperty(
        description="Show only new menus", update=update_tree
    )
    # show_pm = BoolProperty(
    #     default=True, description="Show pie menus",
    #     update=update_tree)
    # show_rm = BoolProperty(
    #     default=True, description="Show regular menus",
    #     update=update_tree)
    # show_pd = BoolProperty(
    #     default=True, description="Show popup dialogs",
    #     update=update_tree)
    # show_pg = BoolProperty(
    #     default=True, description="Show panel groups",
    #     update=update_tree)
    # show_hpg = BoolProperty(
    #     default=True, description="Show hidden panel groups",
    #     update=update_tree)
    # show_scripts = BoolProperty(
    #     default=True, description="Show stack keys",
    #     update=update_tree)
    # show_sticky = BoolProperty(
    #     default=True, description="Show sticky keys",
    #     update=update_tree)
    # show_macro = BoolProperty(
    #     default=True, description="Show macro operators",
    #     update=update_tree)
    cache_scripts = BoolProperty(
        name="Cache External Scripts", description="Cache external scripts",
        default=True)
    panel_info_visibility = EnumProperty(
        name="Panel Info",
        description="Show panel info",
        items=(
            ('NAME', "Name", "", 'SYNTAX_OFF', 1),
            ('CLASS', "Class", "", 'SYNTAX_ON', 2),
            ('CTX', "Context", "", 'NODE', 4),
            ('CAT', "Category", "", 'LINENUMBERS_ON', 8),
        ),
        default={'NAME', 'CLASS'},
        options={'ENUM_FLAG'}
    )
    restore_mouse_pos = BoolProperty(
        name="Restore Mouse Position (Pie Menu)",
        description=(
            "Restore mouse position "
            "after releasing the pie menu's hotkey"))
    use_spacer = BoolProperty(
        name="Use 'Spacer' Separator by Default (Popup Dialog)",
        description="Use 'Spacer' separator by default",
        default=False)
    use_cmd_editor = BoolProperty(
        name="Use Operator Properties Editor (Command Tab)",
        description="Use operator properties editor",
        default=True)

    def get_debug_mode(self):
        return bpy.app.debug_wm

    def set_debug_mode(self, value):
        bpy.app.debug_wm = value

    debug_mode = BoolProperty(
        get=get_debug_mode, set=set_debug_mode,
        description="Debug Mode")

    def update_tree_mode(self, context):
        PME_UL_pm_tree.update_tree()

    tree_mode = BoolProperty(
        description="Tree Mode", update=update_tree_mode)

    def get_maximize_prefs(self):
        return bpy.types.USERPREF_PT_addons.draw == draw_addons_maximized

    def set_maximize_prefs(self, value):
        if value and not is_userpref_maximized():
            bpy.ops.pme.userpref_show(addon="pie_menu_editor")

        elif not value and is_userpref_maximized():
            bpy.ops.pme.userpref_restore()

    maximize_prefs = BoolProperty(
        description="Maximize preferences area",
        get=get_maximize_prefs, set=set_maximize_prefs)

    button_scalex = FloatProperty(
        default=1, step=10, min=0.5, max=2,
        description="Width of the buttons")
    pmi_data = PointerProperty(type=PMIData)
    scripts_filepath = StringProperty(subtype='FILE_PATH', default=SCRIPT_PATH)

    @property
    def selected_pm(self):
        if 0 <= self.active_pie_menu_idx < len(self.pie_menus):
            return self.pie_menus[self.active_pie_menu_idx]
        return None

    @property
    def mode(self):
        return PMEPreferences._mode

    @mode.setter
    def mode(self, value):
        PMEPreferences._mode = value

    def enter_mode(self, mode):
        self.mode_history.append(PMEPreferences._mode)
        PMEPreferences._mode = mode

    def leave_mode(self):
        PMEPreferences._mode = self.mode_history.pop()

    def is_edit_mode(self):
        return 'PMI' in PMEPreferences.mode_history

    def add_pm(self, mode='PMENU', name=None, duplicate=False):
        link = None
        tpr = temp_prefs()

        if self.tree_mode and len(tpr.links):
            link = tpr.links[tpr.links_idx]
            if link.path:
                self.active_pie_menu_idx = self.pie_menus.find(link.path[0])

        tpr.links_idx = -1

        self.pie_menus.add()
        if self.active_pie_menu_idx < len(self.pie_menus) - 1:
            self.active_pie_menu_idx += 1
        self.pie_menus.move(len(self.pie_menus) - 1, self.active_pie_menu_idx)
        pm = self.selected_pm

        pm.mode = mode
        pm.name = self.unique_pm_name(name or pm.ed.default_name)

        if self.tree_mode and self.show_keymap_names and not duplicate and link:
            if link.label:
                pm.km_name = link.label
            elif link.path and link.path[0] in self.pie_menus:
                pm.km_name = self.pie_menus[link.path[0]].km_name
            elif link.pm_name and link.pm_name in self.pie_menus:
                pm.km_name = self.pie_menus[link.pm_name].km_name

            if pm.km_name in PME_UL_pm_tree.collapsed_km_names:
                PME_UL_pm_tree.collapsed_km_names.remove(pm.km_name)

        pm.data = pm.ed.default_pmi_data

        if mode == 'PMENU':
            for i in range(0, 8):
                pm.pmis.add()

        if mode == 'RMENU' and not duplicate:
            pmi = pm.pmis.add()
            pmi.mode = 'COMMAND'
            pmi.name = "Menu Item"

        elif mode == 'STICKY' and not duplicate:
            pmi = pm.pmis.add()
            pmi.mode = 'COMMAND'
            pmi.name = "On Press"
            pmi = pm.pmis.add()
            pmi.mode = 'COMMAND'
            pmi.name = "On Release"

        elif mode == 'SCRIPT' and not duplicate:
            pmi = pm.pmis.add()
            pmi.mode = 'COMMAND'
            pmi.name = "Command 1"

        elif mode == 'MACRO' and not duplicate:
            pmi = pm.pmis.add()
            pmi.mode = 'COMMAND'
            pmi.name = "Command 1"
            add_macro(pm)

        elif mode == 'DIALOG' and not duplicate:
            pm.ed.add_pd_row(pm)

        pm.register_hotkey()

        return pm

    def remove_pm(self, pm=None):
        tpr = temp_prefs()
        idx = 0

        if pm:
            idx = self.pie_menus.find(pm.name)
        else:
            idx = self.active_pie_menu_idx

        if idx < 0 or idx >= len(self.pie_menus):
            return

        apm = self.pie_menus[idx]
        new_idx = -1
        num_links = len(tpr.links)
        if self.tree_mode and num_links:
            d = 1
            i = tpr.links_idx + d
            while True:
                if i >= num_links:
                    d = -1
                    i = tpr.links_idx + d
                    continue
                if i < 0:
                    break
                link = tpr.links[i]
                if not link.label and not link.path and \
                        link.pm_name != apm.name:
                    tpr["links_idx"] = i
                    new_idx = self.pie_menus.find(link.pm_name)
                    break
                i += d

        apm.key_mod = 'NONE'

        if apm.mode == 'PANEL':
            remove_panel_group(apm.name)
        elif apm.mode == 'HPANEL':
            for pmi in apm.pmis:
                unhide_panel(pmi.text)
        elif apm.mode == 'MACRO':
            remove_macro(apm)

        apm.unregister_hotkey()

        if apm.name in self.old_pms:
            self.old_pms.remove(apm.name)

        self.pie_menus.remove(idx)

        if new_idx >= idx:
            new_idx -= 1

        if new_idx >= 0:
            self.active_pie_menu_idx = new_idx
        elif self.active_pie_menu_idx >= len(self.pie_menus) and \
                self.active_pie_menu_idx > 0:
            self.active_pie_menu_idx -= 1

    def unique_pm_name(self, name):
        if name not in self.pie_menus:
            return name

        idx = 1

        mo = re_name_idx.search(name)
        if mo:
            name = mo.group(1)
            idx = int(mo.group(2))

        while True:
            uname = "%s.%s" % (name, str(idx).zfill(3))
            if uname not in self.pie_menus:
                return uname

            idx += 1

    def from_dict(self, value):
        pass

    def to_dict(self):
        d = {}
        return d

    def _draw_pmi(self, context):
        pr = prefs()
        tpr = temp_prefs()
        pm = pr.selected_pm
        layout = self.layout

        lh.lt(layout)
        split = lh.split(None, 0.75, False)
        lh.row()

        data = pr.pmi_data
        icon = data.parse_icon('FILE_HIDDEN')

        if pm.ed.use_slot_icon:
            lh.operator(
                WM_OT_pmi_icon_select.bl_idname, "", icon,
                idx=pme.context.edit_item_idx,
                icon="")

        lh.prop(data, "name", "")

        if data.name != data.sname and data.sname:
            lh.operator(
                PME_OT_pmi_name_apply.bl_idname, "", 'BACK',
                idx=pme.context.edit_item_idx)

            lh.prop(data, "sname", "", enabled=False)

        lh.lt(split)
        lh.operator(
            WM_OT_pmi_data_edit.bl_idname, "OK",
            idx=pme.context.edit_item_idx, ok=True,
            enabled=not data.has_messages())
        lh.operator(WM_OT_pmi_data_edit.bl_idname, "Cancel", idx=-1)

        box = layout.box()
        column = lh.column(box)
        lh.row()
        pm.ed.draw_slot_modes(lh.layout, data)

        if data.mode == 'COMMAND':
            lh.row(column)
            icon = 'ERROR' if data.has_messages() else 'NONE'
            lh.prop(data, "cmd", "", icon)

            lh.operator(
                WM_OT_pmidata_specials_call.bl_idname, "", 'COLLAPSEMENU')

            if pm.mode == 'STICKY' and PME_OT_sticky_key_edit.pmi_prop and \
                    pme.context.edit_item_idx == 0 and not data.has_messages():
                lh.lt(column)
                lh.operator(PME_OT_sticky_key_edit.bl_idname)

        elif data.mode == 'PROP':
            lh.row(column)
            icon = 'ERROR' if data.has_messages() else 'NONE'
            lh.prop(data, "prop", "", icon)

        elif data.mode == 'MENU':
            icon = 'ERROR' if data.has_messages() else 'NONE'
            if data.menu in pr.pie_menus:
                icon = pr.pie_menus[data.menu].ed.icon
            row = lh.row(column)
            row.prop_search(
                data, "menu", tpr, "pie_menus", text="", icon=icon)

            lh.operator(
                WM_OT_pmidata_specials_call.bl_idname, "", 'COLLAPSEMENU')

        elif data.mode == 'HOTKEY':
            lh.row(column)
            icon = 'ERROR' if data.has_messages() else 'NONE'
            lh.prop(data, "key", "", icon, event=True)

            lh.row(column)
            lh.prop(data, "ctrl", "Ctrl", toggle=True)
            lh.prop(data, "shift", "Shift", toggle=True)
            lh.prop(data, "alt", "Alt", toggle=True)
            lh.prop(data, "oskey", "OSkey", toggle=True)
            lh.prop(data, "key_mod", "", event=True)

        elif data.mode == 'CUSTOM':
            lh.row(column)
            icon = 'ERROR' if data.has_messages() else 'NONE'
            lh.prop(data, "custom", "", icon)

            lh.operator(
                WM_OT_pmidata_specials_call.bl_idname, "", 'COLLAPSEMENU')

        # elif data.mode == 'OPERATOR':
        #     lh.row(column)
        #     icon = 'ERROR' if data.has_messages() else 'NONE'
        #     lh.prop(data, "custom", "", icon)

        #     lh.operator(
        #         WM_OT_pmidata_specials_call.bl_idname, "", 'COLLAPSEMENU')

        if data.has_messages():
            lh.box(layout)
            lh.label(data.msg, icon='INFO')

        if pr.use_cmd_editor and data.mode == 'COMMAND' and \
                data.kmi.idname and not data.has_messages():
            lh.lt(layout.box().column(True))

            lh.save()
            lh.row(align=False)
            lh.op(PME_OT_pmi_cmd_generate.bl_idname, icon='FILE_TEXT')
            lh.op(
                PME_OT_pmi_cmd_generate.bl_idname,
                "Clear Properties and Generate", 'FILE_BLANK')(
                clear=True)
            lh.restore()

            lh.sep()

            lh.save()
            lh.row(align=False)
            lh.prop(data, "cmd_ctx", "")
            lh.prop(data, "cmd_undo", toggle=True)
            lh.restore()

            lh.template_keymap_item_properties(data.kmi)

    def _draw_icons(self, context):
        pr = prefs()
        pm = pr.selected_pm
        pmi = pm.pmis[pme.context.edit_item_idx]
        layout = self.layout

        lh.lt(layout)
        split = lh.split(None, 0.75, False)
        lh.row()

        data = pmi
        if pr.is_edit_mode():
            data = pr.pmi_data

        icon = data.parse_icon('FILE_HIDDEN')

        lh.prop(data, "name", "", icon)
        lh.sep()
        lh.prop(pr, "icon_filter", text="", icon='VIEWZOOM')
        if pr.icon_filter:
            lh.operator(WM_OT_icon_filter_clear.bl_idname, "", 'X')

        lh.lt(split)
        lh.operator(
            WM_OT_pmi_icon_select.bl_idname, "None",
            idx=pme.context.edit_item_idx,
            icon='NONE')

        lh.operator(
            WM_OT_pmi_icon_select.bl_idname, "Cancel", idx=-1)

        icon_filter = pr.icon_filter.upper()

        box = layout.box()
        column = box.column(align=True)
        row = column.row(align=True)
        row.alignment = 'CENTER'
        idx = 0

        for k, i in bpy.types.UILayout.bl_rna.functions[
                "prop"].parameters["icon"].enum_items.items():
            icon = i.identifier
            if k == 'NONE':
                continue
            if icon_filter != "" and icon_filter not in icon:
                continue

            p = row.operator(
                WM_OT_pmi_icon_select.bl_idname, text="",
                icon=icon, emboss=False)
            p.idx = pme.context.edit_item_idx
            p.icon = icon
            idx += 1
            if idx > 28:
                idx = 0
                row = column.row(align=True)
                row.alignment = 'CENTER'

        if idx != 0:
            while idx < 29:
                row.label("", icon='BLANK1')
                idx += 1

        row = layout.row(align=True)
        row.prop(
            pr, "show_custom_icons", text="Custom Icons", toggle=True)

        row.operator(
            PME_OT_icons_refresh.bl_idname, "", icon='FILE_REFRESH')

        p = row.operator("wm.path_open", "", icon='FILE_FOLDER')
        p.filepath = ph.path

        if not pr.show_custom_icons:
            return

        icon_filter = pr.icon_filter

        box = layout.box()
        column = box.column(align=True)
        row = column.row(align=True)
        row.alignment = 'CENTER'
        idx = 0

        for icon in sorted(ph.get_names()):
            if icon_filter != "" and icon_filter not in icon:
                continue

            p = row.operator(
                WM_OT_pmi_icon_select.bl_idname, "",
                icon_value=ph.get_icon(icon), emboss=False)
            p.idx = pme.context.edit_item_idx
            p.icon = '@' + icon
            idx += 1
            if idx > 28:
                idx = 0
                row = column.row(align=True)
                row.alignment = 'CENTER'

        if idx != 0:
            while idx < 29:
                row.label("", icon='BLANK1')
                idx += 1

    def _draw_tab_editor(self, context, layout):
        pr = prefs()
        tpr = temp_prefs()
        pm = None
        link = None
        if pr.tree_mode:
            if len(tpr.links) > 0:
                link = tpr.links[tpr.links_idx]
                if link.pm_name:
                    pm = pr.pie_menus[link.pm_name]
        else:
            if len(pr.pie_menus):
                pm = pr.selected_pm

        if pr.show_list:
            split = layout.split(pr.list_size / 100)
            row = split.row()
            column1 = row.column()
            row = split.row()
            column2 = row.column(align=True)
        else:
            row = layout

        column3 = row.column()

        if pr.show_list:
            subrow = column1

            if pr.use_filter:
                subrow = column1.row()
                subcol = subrow.column(True)
                subcol.prop(
                    pr, "mode_filter", "",
                    expand=True, icon_only=True)

                subcol.separator()
                subcol.prop(
                    pr, "show_only_new_pms", "", icon='NEW', toggle=True)

                column1 = subrow.column()

            if pr.tree_mode:
                column1.template_list(
                    "PME_UL_pm_tree", "",
                    tpr, "links",
                    tpr, "links_idx", rows=NUM_LIST_ROWS)
            else:
                column1.template_list(
                    "WM_UL_pm_list", "",
                    self, "pie_menus", self, "active_pie_menu_idx",
                    rows=NUM_LIST_ROWS)
            row = column1.row(align=True)
            p = row.operator(WM_OT_pm_import.bl_idname, text="Import")
            p.mode = ""

            if pm or link:
                p = row.operator(WM_OT_pm_export.bl_idname, text="Export")
                p.mode = ""

            lh.lt(column2)

            lh.operator(
                WM_OT_pm_add.bl_idname, "", 'ZOOMIN',
                mode="")

            if pm:
                lh.operator(WM_OT_pm_duplicate.bl_idname, "", 'GHOST')
                lh.operator(WM_OT_pm_remove.bl_idname, "", 'ZOOMOUT')

            lh.operator(
                WM_OT_pm_remove_all.bl_idname, "", 'X',
                ask=True)

            lh.sep()

            if pm and not pr.tree_mode:
                if not link or not link.path:
                    lh.operator(
                        WM_OT_pm_move.bl_idname, "", 'TRIA_UP',
                        direction=-1)
                    lh.operator(
                        WM_OT_pm_move.bl_idname, "", 'TRIA_DOWN',
                        direction=1)
                lh.operator(
                    WM_OT_pm_sort.bl_idname, "", 'SORTALPHA',
                    mode="")

                lh.sep()

            lh.operator(
                WM_OT_pm_enable_all.bl_idname, "", ICON_ON).enabled = True
            lh.operator(
                WM_OT_pm_enable_all.bl_idname, "", ICON_OFF).enabled = False

            if pr.tree_mode and PME_UL_pm_tree.has_folders:
                lh.sep(group='EXP_COL_ALL')
                icon = 'TRIA_RIGHT' \
                    if PME_UL_pm_tree.expanded_folders else \
                    'TRIA_DOWN'
                lh.operator(PME_OT_tree_folder_toggle_all.bl_idname, "", icon)

            if pr.tree_mode and pr.show_keymap_names and len(pr.pie_menus):
                lh.sep(group='EXP_COL_ALL')
                icon = 'TRIA_DOWN_BAR' \
                    if PME_UL_pm_tree.collapsed_km_names else 'TRIA_RIGHT_BAR'
                lh.operator(
                    PME_OT_tree_kmname_toggle.bl_idname, "", icon,
                    km_name="",
                    idx=-1,
                    all=True)

        if not pm:
            if link and link.label:
                subcol = column3.box().column(True)
                subrow = subcol.row()
                subrow.enabled = False
                subrow.scale_y = NUM_LIST_ROWS + LIST_PADDING
                subrow.alignment = 'CENTER'
                subrow.label(link.label)
                subcol.row(True)
            else:
                subcol = column3.box().column(True)
                subrow = subcol.row()
                subrow.enabled = False
                subrow.scale_y = NUM_LIST_ROWS + LIST_PADDING
                subrow.alignment = 'CENTER'
                subrow.label(" ")
                subcol.row(True)
            return

        row = column3.row(align=True)
        row.prop(
            pm, "enabled", text="",
            icon=ICON_ON if pm.enabled else ICON_OFF)

        if pm.ed.use_preview:
            p = row.operator(
                WM_OT_pme_preview.bl_idname, "", icon='VISIBLE_IPO_ON')
            p.pie_menu_name = pm.name

        p = row.operator(
            WM_OT_pm_select.bl_idname, "", icon=pm.ed.icon)
        p.pm_name = ""
        p.use_mode_icons = True
        row.prop(pm, "label", text="")

        if pm.ed.docs:
            p = row.operator(PME_OT_docs.bl_idname, "", icon='HELP')
            p.id = pm.ed.docs

        if pm.ed.has_extra_settings:
            row.prop(pr, "show_advanced_settings", text="", icon='SETTINGS')

            if pr.show_advanced_settings:
                pm.ed.draw_extra_settings(column3.box(), pm)

        column = column3.column(True)
        pm.ed.draw_keymap(column, pm)
        pm.ed.draw_hotkey(column, pm)
        pm.ed.draw_items(column3, pm)

    def _draw_tab_settings(self, context, layout):
        pr = prefs()

        box = layout.box()
        subrow = box.split(0.5)
        col = subrow.column()

        pr.hotkey.draw(col)
        col.prop(pr, "hold_time")
        col.prop(pr, "list_size", slider=True)

        col = subrow.column()

        subcol = col.column(True)
        subcol.prop(pr, "cache_scripts")
        subcol.prop(pr, "use_spacer")
        subcol.prop(pr, "use_cmd_editor")
        subcol.prop(pr, "restore_mouse_pos")

        pr.overlay.draw(box)

    def _draw_preferences(self, context):
        pr = prefs()
        layout = self.layout

        row = layout.row(True)

        row.prop(pr, "show_list", text="", icon='COLLAPSEMENU')

        if pr.show_list:
            row.prop(pr, "tree_mode", text="", icon='OOPS')
            row.prop(pr, "use_filter", "", icon='FILTER')
            row.prop(pr, "show_names", text="", icon='SYNTAX_OFF')
            row.prop(pr, "show_hotkeys", text="", icon='FONTPREVIEW')
            row.prop(
                pr, "show_keymap_names", text="", icon='SPLITSCREEN')

        row.separator()

        row.prop(pr, "tab", expand=True)

        row.separator()

        row.prop(pr, "interactive_panels", text="", icon='MOD_MULTIRES')
        row.prop(pr, "debug_mode", text="", icon='SCRIPT')

        row.separator()

        row.prop(pr, "maximize_prefs", "", icon='FULLSCREEN_ENTER')

        if pr.tab == 'EDITOR':
            self._draw_tab_editor(context, layout)

        elif pr.tab == 'SETTINGS':
            self._draw_tab_settings(context, layout)

    def draw(self, context):
        if self.mode == 'ADDON':
            self._draw_preferences(context)
        elif self.mode == 'ICONS':
            self._draw_icons(context)
        elif self.mode == 'PMI':
            self._draw_pmi(context)

    def init_menus(self):
        DBG and logh("Init Menus")

        if len(self.pie_menus) == 0:
            self.add_pm()
            return

        for pm in self.pie_menus:
            self.old_pms.add(pm.name)

            if not pm.data and pm.mode in {'PMENU', 'RMENU', 'DIALOG'}:
                pm.data = pm.ed.default_pmi_data

            if pm.mode == 'SCRIPT':
                if not pm.data.startswith("s?"):
                    pmi = pm.pmis.add()
                    pmi.text = pm.data
                    pmi.mode = 'COMMAND'
                    pmi.name = "Command 1"
                    pm.data = pm.ed.default_pmi_data

            if pm.mode not in {'PANEL', 'HPANEL', 'SCRIPT'}:
                for pmi in pm.pmis:
                    if pmi.mode == 'MENU' and pmi.text[0] == "@":
                        get_pme_menu_class(pmi.text[1:])

            if pm.mode == 'HPANEL' and pm.enabled and not SAFE_MODE:
                for pmi in pm.pmis:
                    hide_panel(pmi.text)

            if pm.mode == 'PANEL' and pm.enabled:
                for i, pmi in enumerate(pm.pmis):
                    add_panel(
                        pm.name, i, pmi.text, pmi.name,
                        pm.panel_space, pm.panel_region,
                        pm.panel_context, pm.panel_category,
                        draw_pme_panel, poll_pme_panel)

            if pm.mode == 'MACRO' and pm.enabled:
                add_macro(pm)

            km_names = pm.parse_keymap(False)
            if km_names:
                for km_name in km_names:
                    if km_name not in self.missing_kms:
                        self.missing_kms[km_name] = []
                    self.missing_kms[km_name].append(pm.name)
                DBG and logw("..." + pm.name, pm.km_name, km_names)
            else:
                DBG and logi(" + " + pm.name)
                pm.register_hotkey()


def register():
    if not hasattr(bpy.types.WindowManager, "pme"):
        bpy.types.WindowManager.pme = bpy.props.PointerProperty(
            type=PMEData)

    PMEPreferences.kh = KeymapHelper()

    pr = prefs()
    pr.tree.lock()
    pr.init_menus()

    pme.context.add_global("_prefs", prefs)
    pme.context.add_global("prefs", prefs)
    pme.context.add_global("pme", pme)
    pme.context.add_global("os", os)
    pme.context.add_global("PMEData", PMEData)

    pr.interactive_panels = False
    pr.icon_filter = ""
    pr.show_custom_icons = False
    pr.tab = 'EDITOR'
    pr.use_filter = False
    pr.show_only_new_pms = False
    pr.maximize_prefs = False
    pr.show_advanced_settings = False

    h = pr.hotkey
    if h.key == 'NONE':
        h.key = 'ACCENT_GRAVE'
        h.ctrl = True
        h.shift = True

    if pr.kh.available():
        pr.kh.keymap()
        h.add_kmi(pr.kh.operator(
            WM_OT_pm_edit,
            key=h.key, ctrl=h.ctrl, shift=h.shift, alt=h.alt, oskey=h.oskey,
            key_mod=h.key_mod)).properties.auto = True

        pr.kh.keymap("Info")
        h.add_kmi(pr.kh.operator(
            WM_OT_pm_edit,
            key=h.key, ctrl=h.ctrl, shift=h.shift, alt=h.alt, oskey=h.oskey,
            key_mod=h.key_mod)).properties.auto = False

        pr.kh.keymap("View2D Buttons List")
        p = pr.kh.operator(
            WM_OT_pmi_icon_select,
            'ESC').properties
        p.idx = -1
        p.hotkey = True

        p = pr.kh.operator(
            WM_OT_pmi_data_edit,
            'RET').properties
        p.ok = True
        p.hotkey = True

        p = pr.kh.operator(
            WM_OT_pmi_data_edit,
            'ESC').properties
        p.idx = -1
        p.hotkey = True

    pr.tree.unlock()
    pr.tree.update()


def unregister():
    pr = prefs()
    pr.kh.unregister()
    PMIData._kmi = None

