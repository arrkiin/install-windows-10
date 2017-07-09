import bpy
from .ed_base import (
    EditorBase, PME_OT_pmi_copy, PME_OT_pmi_paste, WM_OT_pmi_data_edit,
    WM_OT_pmi_icon_select, WM_OT_pmi_icon_tag_toggle)
from .addon import prefs
from .constants import ICON_ON, ICON_OFF, SPACER_SCALE_Y, SCALE_X
from .layout_helper import lh, draw_pme_layout, Row
from .ui import tag_redraw, shorten_str
from .debug_utils import *
from .operators import popup_dialog_pie
from . import pme


current_pdi = 0
cur_row = Row()
prev_row = Row()


class WM_OT_pdi_add(bpy.types.Operator):
    bl_idname = "wm.pdi_add"
    bl_label = "Add Row or Button"
    bl_description = "Add a row or a button"
    bl_options = {'INTERNAL'}

    mode = bpy.props.StringProperty()
    index = bpy.props.IntProperty()

    def execute(self, context):
        pr = prefs()
        pm = pr.selected_pm

        if self.mode == 'BUTTON':
            pm.ed.add_pd_button(pm, self.index)
            if pr.use_spacer:
                sp_idx = self.index
                if self.index == current_pdi:
                    sp_idx += 1
                spacer = pm.ed.add_pd_spacer(pm, sp_idx)
                spacer.text = "spacer?hsep=SPACER"

        elif self.mode == 'ROW':
            pm.ed.add_pd_row(pm, self.index)

        elif self.mode == 'SPLIT':
            prev = pm.pmis[self.index - 1]
            if prev.mode == 'EMPTY' and prev.text.startswith("spacer"):
                pm.pmis.remove(self.index - 1)
                self.index -= 1

            pm.ed.add_pd_row(pm, self.index, True)

        tag_redraw()
        return {'FINISHED'}


class WM_OT_pdi_move(bpy.types.Operator):
    bl_idname = "wm.pdi_move"
    bl_label = ""
    bl_description = "Move an item"
    bl_options = {'INTERNAL'}

    pm_item = bpy.props.IntProperty()
    idx = bpy.props.IntProperty()

    def _draw(self, menu, context):
        pm = prefs().selected_pm

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
                WM_OT_pdi_move.bl_idname, text, icon,
                pm_item=self.pm_item,
                idx=idx)

        draw_pme_layout(pm, column, draw_pmi)

    def execute(self, context):
        pm = prefs().selected_pm

        if self.idx != self.pm_item:
            pm.pmis.move(self.pm_item, self.idx)
            idx2 = \
                self.idx - 1 if self.pm_item < self.idx else self.idx + 1
            if idx2 != self.pm_item:
                pm.pmis.move(idx2, self.pm_item)

        tag_redraw()
        return {'FINISHED'}

    def invoke(self, context, event):
        if self.idx == -1:
            popup_dialog_pie(event, self._draw)
        else:
            self.execute(context)

        return {'FINISHED'}


class WM_OT_prop_set(bpy.types.Operator):
    bl_idname = "wm.prop_set"
    bl_label = ""
    bl_options = {'INTERNAL'}

    mode = bpy.props.StringProperty()
    prop = bpy.props.StringProperty()
    value = bpy.props.StringProperty()

    def execute(self, context):
        pr = prefs()
        pp = pme.props
        pm = pr.selected_pm

        if self.mode == 'ROW':
            row = pm.pmis[cur_row.a]
            row.text = pme.props.encode(
                row.text, self.prop, self.value)

            tag_redraw()

        elif self.mode == 'PDI':
            prev_pdi = pm.pmis[current_pdi - 1]
            if prev_pdi.mode == 'EMPTY' and prev_pdi.text.startswith("spacer"):
                prop = pp.parse(prev_pdi.text)
                remove_subrows = False
                if prop.hsep == 'COLUMN' and \
                        self.prop == "hsep" and self.value != 'COLUMN' and \
                        cur_row.num_columns == 2:
                    remove_subrows = True

                if prop.subrow == 'END' and \
                        self.prop == "hsep" and self.value == 'COLUMN':
                    prev_pdi.text = pp.encode(prev_pdi.text, "subrow", 'NONE')

                prev_pdi.text = pp.encode(
                    prev_pdi.text, self.prop, self.value)
                if self.value == 'NONE' and \
                        pp.parse(prev_pdi.text).is_empty:
                    pm.pmis.remove(current_pdi - 1)
                    cur_row.b -= 1

                if remove_subrows:
                    cur_row.remove_subrows(pm)

            else:
                prev_pdi = pm.ed.add_pd_spacer(pm, current_pdi)
                prev_pdi.text = pp.encode(
                    prev_pdi.text, self.prop, self.value)
                cur_row.b += 1

            if self.prop == "hsep" and self.value == 'COLUMN':
                pmi = cur_row.b < len(pm.pmis) and pm.pmis[cur_row.b]
                if pmi and pp.parse(pmi.text).vspacer == 'NONE':
                    pmi.text = pp.encode(pmi.text, "vspacer", 'NORMAL')

            tag_redraw()

        return {'FINISHED'}


class WM_OT_pmi_clear(bpy.types.Operator):
    bl_idname = "wm.pmi_clear"
    bl_label = "Clear"
    bl_description = "Clear an item"
    bl_options = {'INTERNAL'}

    pm_item = bpy.props.IntProperty()
    delete = bpy.props.BoolProperty()

    def execute(self, context):
        pr = prefs()
        pp = pme.props
        pm = pr.selected_pm
        pmi = pm.pmis[self.pm_item]

        def merge():
            pmi = self.pm_item < len(pm.pmis) and pm.pmis[self.pm_item]
            prev = self.pm_item - 1 < len(pm.pmis) and pm.pmis[
                self.pm_item - 1]
            ret = False

            if prev and prev.mode == 'EMPTY' and pmi and pmi.mode == 'EMPTY':
                pprop = pp.parse(prev.text)
                prop = pp.parse(pmi.text)

                if pprop.type == "row" and prop.type == "spacer":
                    if prop.hsep != 'NONE':
                        ret = True
                        pmi.text = pp.encode(pmi.text, "hsep", 'NONE')
                        if pp.parse(pmi.text).is_empty:
                            pm.pmis.remove(self.pm_item)

                elif pprop.type == "spacer" and prop.type == "row":
                    ret = True
                    pm.pmis.remove(self.pm_item - 1)
                    self.pm_item -= 1

                elif pprop.type == "spacer" and prop.type == "spacer":
                    if pprop.subrow == 'BEGIN' and prop.subrow == 'BEGIN':
                        ret = True
                        pmi.text = pp.encode(pmi.text, "subrow", 'NONE')
                        if pp.parse(pmi.text).is_empty:
                            pm.pmis.remove(self.pm_item)

                    elif pprop.subrow == 'BEGIN' and prop.subrow == 'END':
                        ret = True
                        pmi.text = pp.encode(pmi.text, "subrow", 'NONE')
                        if pp.parse(pmi.text).is_empty:
                            pm.pmis.remove(self.pm_item)

                        prev.text = pp.encode(
                            prev.text, "subrow", 'NONE')
                        if pp.parse(prev.text).is_empty:
                            pm.pmis.remove(self.pm_item - 1)
                            self.pm_item -= 1

                    elif pprop.subrow != 'NONE' and prop.subrow == 'COLUMN':
                        ret = True
                        pm.pmis.remove(self.pm_item - 1)
                        self.pm_item -= 1

                    elif pprop.hsep == 'COLUMN' and prop.hsep == 'SPACER':
                        pmi.text = pp.encode(pmi.text, "hsep", 'NONE')
                        ret = True
                        if pp.parse(pmi.text).is_empty:
                            pm.pmis.remove(self.pm_item)

                    elif pprop.hsep == 'SPACER' and prop.hsep == 'COLUMN':
                        prev.text = pp.encode(prev.text, "hsep", 'NONE')
                        ret = True
                        if pp.parse(prev.text).is_empty:
                            pm.pmis.remove(self.pm_item - 1)
                            self.pm_item -= 1

                    elif pprop.hsep == 'COLUMN' and prop.hsep == 'COLUMN':
                        ret = True
                        pm.pmis.remove(self.pm_item)

                    elif pprop.hsep == 'SPACER' and prop.hsep == 'SPACER':
                        ret = True
                        pm.pmis.remove(self.pm_item)

            elif prev and prev.mode == 'EMPTY' and not pmi:
                ret = True
                pm.pmis.remove(self.pm_item - 1)
                self.pm_item -= 1

            return ret

        if self.delete:
            pm.pmis.remove(self.pm_item)
            if pm.mode == 'DIALOG':
                while merge():
                    pass
                self.pm_item -= 1
                row = Row()
                row.find_ab(pm, self.pm_item)
                row.find_columns(pm)
                if row.num_columns < 2:
                    row.remove_subrows(pm)

        else:
            pmi.text = ""
            pmi.name = ""
            pmi.icon = ""
            pmi.mode = 'EMPTY'

        pr.update_tree()
        tag_redraw()

        return {'CANCELLED'}


class WM_OT_pdr_copy(bpy.types.Operator):
    bl_idname = "wm.pdr_copy"
    bl_label = "Copy Row"
    bl_description = "Copy the row"
    bl_options = {'INTERNAL'}

    row_idx = bpy.props.IntProperty()
    row_last_idx = bpy.props.IntProperty()

    def execute(self, context):
        pr = prefs()
        pm = pr.selected_pm

        if not pr.pdr_clipboard:
            tag_redraw()

        pr.pdr_clipboard = []

        for i in range(self.row_idx, self.row_last_idx):
            pmi = pm.pmis[i]
            pr.pdr_clipboard.append((pmi.name, pmi.icon, pmi.mode, pmi.text))

        return {'FINISHED'}


class WM_OT_pdr_paste(bpy.types.Operator):
    bl_idname = "wm.pdr_paste"
    bl_label = "Paste Row"
    bl_description = "Paste the row"
    bl_options = {'INTERNAL'}

    row_idx = bpy.props.IntProperty()
    row_last_idx = bpy.props.IntProperty()

    def execute(self, context):
        pr = prefs()
        pm = pr.selected_pm

        last_idx = len(pm.pmis)
        idx = self.row_idx

        for row in pr.pdr_clipboard:
            pmi = pm.pmis.add()
            pmi.name = row[0]
            pmi.icon = row[1]
            pmi.mode = row[2]
            pmi.text = row[3]

            if self.row_idx != -1:
                pm.pmis.move(last_idx, idx)
                last_idx += 1
                idx += 1

        tag_redraw()
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return prefs().pdr_clipboard is not None


class WM_OT_pd_row_move(bpy.types.Operator):
    bl_idname = "wm.pd_row_move"
    bl_label = ""
    bl_description = "Move the row"
    bl_options = {'INTERNAL'}

    row_idx = bpy.props.IntProperty()
    move_idx = bpy.props.IntProperty()
    rows = []

    def _draw(self, menu, context):
        lh.lt(menu.layout)

        idx = 0
        for idx, row in enumerate(WM_OT_pd_row_move.rows):
            icon = 'SPACE2' if self.row_idx == row[0] else 'SPACE3'
            lh.operator(
                WM_OT_pd_row_move.bl_idname, "Row %d" % (idx + 1), icon,
                move_idx=idx,
                row_idx=self.row_idx)

        lh.operator(
            WM_OT_pd_row_move.bl_idname, ". . .", 'SPACE3',
            move_idx=idx + 1,
            row_idx=self.row_idx)

    def execute(self, context):
        pm = prefs().selected_pm

        if self.move_idx == -1:
            rows = []
            row_idx = -1
            for idx, pmi in enumerate(pm.pmis):
                if pmi.mode == 'EMPTY' and pmi.text.startswith("row"):
                    if row_idx == -1:
                        row_idx = idx
                    else:
                        rows.append((row_idx, idx))
                        row_idx = idx
            if row_idx != -1:
                rows.append((row_idx, idx + 1))

            WM_OT_pd_row_move.rows = rows

            context.window_manager.popup_menu(
                self._draw, title=WM_OT_pd_row_move.bl_description)

        else:
            if self.move_idx < len(WM_OT_pd_row_move.rows):
                move_idx = WM_OT_pd_row_move.rows[self.move_idx][0]
            else:
                move_idx = WM_OT_pd_row_move.rows[-1][1]

            for row in WM_OT_pd_row_move.rows:
                if row[0] == self.row_idx:
                    row_idx, row_last_idx = row
                    break

            if move_idx == row_idx or move_idx == row_last_idx:
                return {'CANCELLED'}

            for i in range(0, row_last_idx - row_idx):
                if row_idx < move_idx:
                    pm.pmis.move(row_last_idx - 1 - i, move_idx - 1 - i)
                else:
                    pm.pmis.move(row_idx + i, move_idx + i)

            tag_redraw()

        return {'FINISHED'}


class WM_OT_pd_row_remove(bpy.types.Operator):
    bl_idname = "wm.pd_row_remove"
    bl_label = ""
    bl_description = "Remove the row"
    bl_options = {'INTERNAL'}

    row_idx = bpy.props.IntProperty()
    row_last_idx = bpy.props.IntProperty()
    ask = bpy.props.BoolProperty()
    mode = bpy.props.StringProperty()

    def _draw(self, menu, context):
        lh.lt(menu.layout)
        lh.operator(
            WM_OT_pd_row_remove.bl_idname, "Remove", 'X',
            row_idx=self.row_idx,
            row_last_idx=self.row_last_idx,
            ask=False)

    def execute(self, context):
        pm = prefs().selected_pm

        if self.mode == 'JOIN':
            pm.pmis.remove(self.row_idx)
            tag_redraw()
            return {'FINISHED'}

        if self.ask:
            context.window_manager.popup_menu(
                self._draw, WM_OT_pd_row_remove.bl_description)
        else:
            for i in range(self.row_idx, self.row_last_idx):
                pm.pmis.remove(self.row_idx)

            tag_redraw()

        return {'FINISHED'}


class WM_MT_pd_row_alignment(bpy.types.Menu):
    bl_label = "Row Alignment"

    def draw(self, context):
        pr = prefs()
        pp = pme.props
        pm = prefs().selected_pm
        row = pm.pmis[cur_row.a]
        lh.lt(self.layout)

        for item in pme.props.get("align").items:
            lh.operator(
                WM_OT_prop_set.bl_idname, item[1],
                'SPACE2' if pp.parse(
                    row.text).align == item[0] else 'SPACE3',
                mode='ROW',
                prop="align",
                value=item[0])


class WM_MT_pd_row_size(bpy.types.Menu):
    bl_label = "Row Size"

    def draw(self, context):
        pr = prefs()
        pp = pme.props
        pm = pr.selected_pm
        row = pm.pmis[cur_row.a]
        lh.lt(self.layout)

        for item in pme.props.get("size").items:
            lh.operator(
                WM_OT_prop_set.bl_idname, item[1],
                'SPACE2' if pp.parse(
                    row.text).size == item[0] else 'SPACE3',
                mode='ROW',
                prop="size",
                value=item[0])


class WM_MT_pd_row_spacer(bpy.types.Menu):
    bl_label = "Row Spacer"

    def draw(self, context):
        pr = prefs()
        pm = pr.selected_pm
        row = pm.pmis[cur_row.a]
        lh.lt(self.layout)

        for item in pme.props.get("vspacer").items:
            if item[0] == 'NONE' and prev_row.num_columns > 0:
                continue
            lh.operator(
                WM_OT_prop_set.bl_idname, item[1],
                'SPACE2' if pme.props.parse(
                    row.text).vspacer == item[0] else 'SPACE3',
                mode='ROW',
                prop="vspacer",
                value=item[0])


class WM_MT_pdi_separator(bpy.types.Menu):
    bl_label = "Spacer"

    def draw(self, context):
        pr = prefs()
        pp = pme.props
        pm = pr.selected_pm
        prev_pmi = pm.pmis[current_pdi - 1]
        lh.lt(self.layout)

        for item in pme.props.get("hsep").items:
            icon = 'SPACE3'
            if prev_pmi.mode == 'EMPTY' and \
                    pp.parse(prev_pmi.text).hsep == item[0] or \
                    prev_pmi.mode != 'EMPTY' and item[0] == 'NONE':
                icon = 'SPACE2'

            lh.operator(
                WM_OT_prop_set.bl_idname, item[1], icon,
                mode='PDI',
                prop="hsep",
                value=item[0])


class WM_OT_pdi_subrow_set(bpy.types.Operator):
    bl_idname = "wm.pdi_subrow_set"
    bl_label = ""
    bl_description = "Mark as a subrow"
    bl_options = {'INTERNAL'}

    mode = bpy.props.StringProperty()
    value = bpy.props.StringProperty()

    def execute(self, context):
        pm = prefs().selected_pm

        def set_subrow_value(idx, new_idx):
            pp = pme.props
            pmi = pm.pmis[idx]
            if pmi.mode == 'EMPTY' and pmi.text.startswith("spacer"):
                prop = pp.parse(pmi.text)

                set_value(pmi, idx, prop, self.value)
            else:
                pmi = pm.ed.add_pd_spacer(pm, new_idx)
                pmi.text = pp.encode(pmi.text, "subrow", self.value)

        def set_value(pmi, idx, prop, value):
            if value == 'NONE' and prop.hsep == 'NONE':
                pm.pmis.remove(idx)
            else:
                pmi.text = pme.props.encode(
                    pmi.text, "subrow", value)

        def remove_subrows(idx, mode):
            i = idx
            if self.mode == 'BEGIN':
                i += 1
            elif self.mode == 'END':
                i += 2
            while i < len(pm.pmis):
                pmi = pm.pmis[i]
                if pmi.mode == 'EMPTY':
                    if pmi.text.startswith("row"):
                        break

                    prop = pme.props.parse(pmi.text)
                    if prop.subrow == mode:
                        set_value(pmi, i, prop, 'NONE')
                        break
                    if prop.hsep == 'COLUMN':
                        break
                i += 1

        if self.mode == 'BEGIN':
            set_subrow_value(current_pdi - 1, current_pdi)
            if self.value == 'NONE':
                remove_subrows(current_pdi, 'END')

        elif self.mode == 'END':
            set_subrow_value(current_pdi + 1, current_pdi + 1)

        tag_redraw()

        return {'FINISHED'}


class PME_OT_pdr_fixed_col_set(bpy.types.Operator):
    bl_idname = "pme.pdr_fixed_col_set"
    bl_label = ""
    bl_description = "Use columns with fixed width"
    bl_options = {'INTERNAL'}

    row_idx = bpy.props.IntProperty()
    value = bpy.props.BoolProperty()

    def execute(self, context):
        pm = prefs().selected_pm
        pmi = pm.pmis[self.row_idx]
        pmi.text = pme.props.encode(pmi.text, "fixed_col", self.value)

        tag_redraw()

        return {'FINISHED'}


class WM_OT_pdi_specials_call(bpy.types.Operator):
    bl_idname = "wm.pdi_specials_call"
    bl_label = ""
    bl_description = "Menu"
    bl_options = {'INTERNAL'}

    pm_item = bpy.props.IntProperty()

    def _draw(self, menu, context):
        pr = prefs()
        pm = pr.selected_pm
        pmi = pm.pmis[current_pdi]

        text, icon, oicon, _, _ = pmi.parse()

        def has_column_sep():
            for i in range(self.row_idx, self.row_last_idx):
                pmi = pm.pmis[i]
                if pmi.mode == 'EMPTY' and pmi.text.startswith("spacer"):
                    prop = pme.props.parse(pmi.text)
                    if prop.hsep == 'COLUMN':
                        return True

            return False

        has_col_sep = has_column_sep()

        lh.lt(menu.layout, operator_context='INVOKE_DEFAULT')
        row = lh.row()
        lh.column()
        lh.label(shorten_str(text) if text else "Menu", icon)

        lh.sep(check=True)

        lh.operator(
            WM_OT_pmi_data_edit.bl_idname,
            "Edit Item", 'TEXT',
            idx=self.pm_item,
            ok=False)

        lh.operator(
            WM_OT_pmi_icon_select.bl_idname,
            "Change Icon", 'FILE_HIDDEN',
            idx=self.pm_item,
            icon="")

        if oicon or pmi.mode == 'PROP':
            lh.operator(
                WM_OT_pmi_icon_tag_toggle.bl_idname, "Hide Text",
                ICON_ON if "#" in pmi.icon else ICON_OFF,
                idx=self.pm_item,
                tag="#")

        lh.operator(
            WM_OT_pmi_icon_tag_toggle.bl_idname, "Visible",
            ICON_ON if "!" not in pmi.icon else ICON_OFF,
            idx=self.pm_item,
            tag="!")

        lh.sep(check=True)

        lh.operator(
            WM_OT_pdi_add.bl_idname, "Add Item", 'BACK',
            index=self.pm_item,
            mode='BUTTON')

        lh.operator(
            WM_OT_pdi_add.bl_idname, "Add Item", 'FORWARD',
            index=self.pm_item + 1,
            mode='BUTTON')

        if not has_col_sep and self.pm_item > self.row_idx + 1:
            lh.operator(
                WM_OT_pdi_add.bl_idname, "Split Row", 'FULLSCREEN_ENTER',
                index=self.pm_item,
                mode='SPLIT')

        lh.sep(check=True)

        lh.operator(
            PME_OT_pmi_copy.bl_idname, None, 'COPYDOWN',
            pm_item=self.pm_item)

        if pr.pmi_clipboard:
            lh.operator(
                PME_OT_pmi_paste.bl_idname, None, 'PASTEDOWN',
                pm_item=self.pm_item)

        lh.sep(check=True)

        lh.operator(
            WM_OT_pdi_move.bl_idname, "Move Item", 'ARROW_LEFTRIGHT',
            pm_item=self.pm_item,
            idx=-1)

        if self.row_last_idx - self.row_idx > 2:
            lh.sep(check=True)
            lh.operator(
                WM_OT_pmi_clear.bl_idname,
                "Remove Item", 'X',
                delete=True,
                pm_item=self.pm_item)
        elif self.row_idx > 0 or self.row_last_idx < len(pm.pmis):
            lh.sep(check=True)
            lh.operator(
                WM_OT_pd_row_remove.bl_idname,
                "Remove Row", 'X',
                row_idx=self.row_idx,
                row_last_idx=self.row_last_idx,
                mode='REMOVE',
                ask=False)

        if self.pm_item > self.row_idx + 1:
            lh.column(row)
            lh.label("Separator")

            lh.sep(check=True)

            prev_pmi = pm.pmis[self.pm_item - 1]

            for item in pme.props.get("hsep").items:
                if item[0] == 'COLUMN' and \
                                self.subrow_idx != -1 and self.subrow_has_end:
                    continue
                icon = 'RADIOBUT_OFF'
                if prev_pmi.mode == 'EMPTY' and \
                        pme.props.parse(
                            prev_pmi.text).hsep == item[0] or \
                        prev_pmi.mode != 'EMPTY' and item[0] == 'NONE':
                    icon = 'RADIOBUT_ON'

                lh.operator(
                    WM_OT_prop_set.bl_idname, item[1], icon,
                    mode='PDI',
                    prop="hsep",
                    value=item[0])

        if has_col_sep:
            lh.column(row)
            lh.label("Column")
            lh.sep(check=True)

            # begin_value = is_begin_subrow()
            begin_value = self.subrow_idx == self.pm_item - 1
            lh.operator(
                WM_OT_pdi_subrow_set.bl_idname,
                "Begin Subrow",
                ICON_ON if begin_value else ICON_OFF,
                mode='BEGIN',
                value='NONE' if begin_value else 'BEGIN')

            # end_value = is_end_subrow()
            end_value = -1
            if self.subrow_has_end:
                if self.subrow_last_idx == self.pm_item + 1:
                    end_value = 1
            else:
                if self.subrow_last_idx == self.pm_item + 1:
                    pass
                elif self.subrow_idx != -1:
                    end_value = 0

            if end_value != -1:
                lh.operator(
                    WM_OT_pdi_subrow_set.bl_idname,
                    "End Subrow",
                    ICON_ON if end_value else ICON_OFF,
                    mode='END',
                    value='NONE' if end_value else 'END')

    def execute(self, context):
        pr = prefs()
        pp = pme.props
        pm = pr.selected_pm

        cur_row.find_ab(pm, self.pm_item)
        cur_row.find_columns(pm)
        prev_row.find_ab(pm, cur_row.a - 1)
        prev_row.find_columns(pm)

        self.row_idx = cur_row.a
        self.row_last_idx = cur_row.b

        self.row_idx = self.pm_item
        self.subrow_idx = -2
        while self.row_idx > 0:
            pmi = pm.pmis[self.row_idx]
            if pmi.mode == 'EMPTY':
                if pmi.text.startswith("row"):
                    break
                elif pmi.text.startswith("spacer") and self.subrow_idx == -2:
                    prop = pp.parse(pmi.text)
                    if prop.hsep == 'COLUMN':
                        self.subrow_idx = -1
                    if prop.subrow == 'BEGIN':
                        self.subrow_idx = self.row_idx
                    elif prop.subrow == 'END':
                        self.subrow_idx = -1
            self.row_idx -= 1

        self.row_last_idx = self.pm_item
        self.subrow_last_idx = -2
        self.subrow_has_end = False
        while self.row_last_idx < len(pm.pmis):
            pmi = pm.pmis[self.row_last_idx]
            if pmi.mode == 'EMPTY':
                if pmi.text.startswith("row"):
                    break
                elif pmi.text.startswith("spacer") and \
                        self.subrow_last_idx == -2:
                    prop = pp.parse(pmi.text)
                    if prop.subrow == 'END':
                        self.subrow_has_end = True
                        self.subrow_last_idx = self.row_last_idx
                    elif prop.subrow == 'BEGIN':
                        self.subrow_last_idx = self.row_last_idx
                    if prop.hsep == 'COLUMN':
                        self.subrow_last_idx = self.row_last_idx
            self.row_last_idx += 1

        if self.subrow_idx == -2:
            self.subrow_idx = -1
        if self.subrow_last_idx == -2:
            self.subrow_last_idx = self.row_last_idx

        global current_pdi
        current_pdi = self.pm_item

        pmi = pm.pmis[self.pm_item]
        context.window_manager.popup_menu(self._draw)

        return {'FINISHED'}


class WM_OT_pd_row_specials_call(bpy.types.Operator):
    bl_idname = "wm.pd_row_specials_call"
    bl_label = ""
    bl_description = "Menu"
    bl_options = {'INTERNAL'}

    row_idx = bpy.props.IntProperty()

    def _draw(self, menu, context):
        pr = prefs()
        pm = pr.selected_pm

        lh.lt(menu.layout, operator_context='INVOKE_DEFAULT')

        lh.menu(
            WM_MT_pd_row_alignment.__name__, "Alignment", 'ALIGN')
        lh.menu(
            WM_MT_pd_row_size.__name__, "Size", 'UV_FACESEL')

        if self.row_idx > 0:
            lh.menu(
                WM_MT_pd_row_spacer.__name__, "Spacer", 'SEQ_SEQUENCER')

        r = Row()
        r.find_ab(pm, self.row_idx)
        has_columns = r.has_columns(pm)
        if has_columns:
            row_prop = pme.props.parse(pm.pmis[self.row_idx].text)
            lh.operator(
                PME_OT_pdr_fixed_col_set.bl_idname,
                "Fixed Columns",
                ICON_ON if row_prop.fixed_col else ICON_OFF,
                row_idx=self.row_idx,
                value=False if row_prop.fixed_col else True)

        lh.sep(check=True)

        lh.operator(
            WM_OT_pdi_add.bl_idname, "Add Row", 'ZOOMIN',
            index=self.row_idx,
            mode='ROW')

        if self.row_last_idx < len(pm.pmis):
            lh.operator(
                WM_OT_pd_row_remove.bl_idname, "Join Row", 'FULLSCREEN_EXIT',
                row_idx=self.row_last_idx,
                mode='JOIN')

        lh.sep(check=True)

        lh.operator(
            WM_OT_pdr_copy.bl_idname, "Copy Row", 'COPYDOWN',
            row_idx=self.row_idx,
            row_last_idx=self.row_last_idx)

        if pr.pdr_clipboard:
            lh.operator(
                WM_OT_pdr_paste.bl_idname, "Paste Row", 'PASTEDOWN',
                row_idx=self.row_idx,
                row_last_idx=self.row_last_idx)

        lh.sep(check=True)

        lh.operator(
            WM_OT_pd_row_move.bl_idname, "Move Row", 'ARROW_LEFTRIGHT',
            row_idx=self.row_idx,
            move_idx=-1)

        if self.row_idx > 0 or self.row_last_idx < len(pm.pmis):
            lh.sep(check=True)
            lh.operator(
                WM_OT_pd_row_remove.bl_idname,
                "Remove Row", 'X',
                row_idx=self.row_idx,
                row_last_idx=self.row_last_idx,
                mode='REMOVE',
                ask=True)

    def execute(self, context):
        pm = prefs().selected_pm

        # cur_row = Row()
        # prev_row = Row()

        prev_row.find_ab(pm, self.row_idx - 1)
        prev_row.find_columns(pm)
        cur_row.find_ab(pm, self.row_idx)
        cur_row.find_columns(pm)

        self.row_last_idx = cur_row.b

        context.window_manager.popup_menu(
            self._draw, title="Row")

        return {'FINISHED'}


pme.props.EnumProperty(
    "row", "align", 'CENTER', [
        ('CENTER', "Center", 0),
        ('LEFT', "Left", 0),
        ('RIGHT', "Right", 0),
    ])
pme.props.EnumProperty(
    "row", "size", 'NORMAL', [
        ('NORMAL', "Normal", 1),
        ('LARGE', "Large", 1.25),
        ('LARGER', "Larger", 1.5),
    ])
pme.props.EnumProperty(
    "row", "vspacer", 'NORMAL', [
        ('NONE', "None", 0),
        ('NORMAL', "Normal", 1),
        ('LARGE', "Large", 3),
        ('LARGER', "Larger", 5),
    ])
pme.props.BoolProperty("row", "fixed_col", False)
pme.props.EnumProperty(
    "spacer", "hsep", 'NONE', [
        ('NONE', "None", ""),
        ('SPACER', "Spacer", ""),
        ('COLUMN', "Column", ""),
    ])
pme.props.EnumProperty(
    "spacer", "subrow", 'NONE', [
        ('NONE', "None", 0),
        ('BEGIN', "Begin", 0),
        ('END', "End", 0),
    ])

pme.props.BoolProperty("pd", "pd_box", True)
pme.props.BoolProperty("pd", "pd_expand")
pme.props.BoolProperty("pd", "pd_panel", True)
pme.props.BoolProperty("pd", "pd_auto_close", False)
pme.props.IntProperty("pd", "pd_width", 300)


class Editor(EditorBase):

    def __init__(self):
        self.id = 'DIALOG'
        EditorBase.__init__(self)

        self.docs = "#Pop-up_Dialog_Editor"
        self.default_pmi_data = "pd?pd_panel=1"
        self.supported_open_modes = {'PRESS', 'HOLD', 'DOUBLE_CLICK'}

    def draw_extra_settings(self, layout, pm):
        EditorBase.draw_extra_settings(self, layout, pm)
        layout.row(True).prop(pm, "pd_panel", expand=True)
        col = layout.column(True)
        col.prop(pm, "pd_expand")
        if pm.pd_panel == 'PANEL':
            # col.prop(pm, "pd_auto_close")
            # if not pm.pd_auto_close:
            if True:
                col.prop(pm, "pd_width")
        else:
            col.prop(pm, "pd_box")

    def draw_items(self, layout, pm):
        pr = prefs()

        row = layout.row()
        column1 = row.box().column(True)
        xrow = column1.row()
        xrow.scale_y = 0
        column2 = row.box()
        column2 = column2.column(True)

        def draw_pdi(pr, pm, pmi, idx):
            text, icon, _, icon_only, hidden = pmi.parse()

            if not text and not hidden:
                # if pmi.mode == 'CUSTOM' or pmi.mode == 'PROP' and (
                if pmi.mode == 'PROP' and (
                        pmi.is_expandable_prop() or icon == 'NONE'):
                    # if icon_only and pmi.mode != 'CUSTOM':
                    if icon_only:
                        text = "[%s]" % pmi.name if pmi.name else " "
                    else:
                        text = pmi.name if pmi.name else " "

            lh.operator(
                WM_OT_pdi_specials_call.bl_idname,
                text, icon,
                pm_item=idx)

        rows = draw_pme_layout(pm, column1, draw_pdi, [])
        DBG_LAYOUT and logi("Rows", rows)

        prev_r = None
        for r in rows:
            if r[0] > 0:
                lh.lt(column2)
                n = r[5]
                if prev_r and prev_r[4] and n == 0:
                    n = 1
                for i in range(0, n):
                    lh.sep()
            row = lh.row(column2)
            row.scale_y = r[1] * r[2] + SPACER_SCALE_Y * r[3]
            lh.operator(
                WM_OT_pd_row_specials_call.bl_idname,
                "", 'COLLAPSEMENU',
                row_idx=r[0])
            prev_r = r

        lh.row(layout)
        lh.operator(
            WM_OT_pdi_add.bl_idname, "Add Row",
            index=-1,
            mode='ROW')

        if pr.pdr_clipboard:
            lh.operator(
                WM_OT_pdr_paste.bl_idname, "Paste Row",
                row_idx=-1)

    def add_pd_button(self, pm, index=-1):
        pmi = pm.pmis.add()
        pmi.mode = 'COMMAND'
        pmi.text = ""
        pmi.name = "My Button"

        idx = len(pm.pmis) - 1
        if index != -1 and index != idx:
            pm.pmis.move(idx, index)

        return pm.pmis[index] if index != -1 else pmi

    def add_pd_spacer(self, pm, index=-1):
        pmi = pm.pmis.add()
        pmi.mode = 'EMPTY'
        pmi.text = "spacer"

        idx = len(pm.pmis) - 1
        if index != -1 and index != idx:
            pm.pmis.move(idx, index)

        return pm.pmis[index] if index != -1 else pmi

    def add_pd_row(self, pm, index=-1, split=False):
        pmi = pm.pmis.add()
        pmi.mode = 'EMPTY'
        pmi.text = "row"

        idx = len(pm.pmis) - 1
        if index != -1 and index != idx:
            pm.pmis.move(idx, index)
            index += 1

        if not split:
            pmi = self.add_pd_button(pm, index)

        return pm.pmis[index] if index != -1 else pmi
