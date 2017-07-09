from . import pme
from .addon import prefs
from .constants import SCALE_X, SPACER_SCALE_Y
from .bl_utils import bp
from .debug_utils import *
from .previews_helper import ph


class LayoutHelper:

    def __init__(self, previews_helper=None):
        self.layout = None
        self.saved_layouts = []
        self.ph = previews_helper
        self.prev_sep_group = None
        self.has_sep = False
        self.parent = None

    def __getattr__(self, name):
        return getattr(self.layout, name, None)

    def blank(self):
        # self.layout.operator("wm.pme_none", "", icon='BLANK1', emboss=False)
        self.layout.label("", icon='BLANK1')
        self.has_sep = False

    def box(
            self, parent=None, operator_context=None,
            enabled=True, alignment='EXPAND'):
        if parent is None:
            parent = self.layout
        self.parent = parent

        self.layout = parent.box()
        self.layout.alignment = alignment
        self.layout.enabled = enabled
        if operator_context is not None:
            self.layout.operator_context = operator_context

        self.has_sep = True
        return self.layout

    def column(
            self, parent=None, align=True, operator_context=None,
            enabled=True):
        if parent is None:
            parent = self.layout
        self.parent = parent

        self.layout = parent.column(align=align)
        self.enabled = enabled
        if operator_context is not None:
            self.layout.operator_context = operator_context

        self.has_sep = True
        return self.layout

    def label(self, text, icon='NONE'):
        icon, icon_value = self.parse_icon(icon)

        self.layout.label(text, icon=icon, icon_value=icon_value)
        self.has_sep = False

    def lt(self, layout, operator_context=None):
        self.layout = layout
        if operator_context is not None:
            layout.operator_context = operator_context
        self.parent = None
        self.has_sep = True
        self.prev_sep_group = None

    def menu(self, menu, text, icon='NONE'):
        icon, icon_value = self.parse_icon(icon)

        self.layout.menu(menu, text, icon=icon, icon_value=icon_value)
        self.has_sep = False

    def operator(
            self, idname, txt=None, icon_id='NONE', enabled=True, emboss=True,
            **props):
        icon_id, icon_value = self.parse_icon(icon_id)

        if not enabled:
            self.save()
            scale_x = self.layout.scale_x
            scale_y = self.layout.scale_y
            self.row(enabled=False)
            self.layout.scale_x = scale_x
            self.layout.scale_y = scale_y

        if txt is None:
            pr = self.layout.operator(
                idname, icon=icon_id, icon_value=icon_value, emboss=emboss)
        else:
            pr = self.layout.operator(
                idname, txt, icon=icon_id, icon_value=icon_value,
                emboss=emboss)
        if props:
            for p in props.keys():
                setattr(pr, p, props[p])

        if not enabled:
            self.restore()

        self.has_sep = False
        return pr

    def op(self, idname, txt=None, icon='NONE', enabled=True, emboss=True):
        def set_props(**props):
            for k, v in props.items():
                setattr(pr, k, v)

            return pr

        icon, icon_value = self.parse_icon(icon)

        if not enabled:
            self.save()
            scale_x = self.layout.scale_x
            scale_y = self.layout.scale_y
            self.row(enabled=False)
            self.layout.scale_x = scale_x
            self.layout.scale_y = scale_y

        if txt is None:
            pr = self.layout.operator(
                idname, icon=icon, icon_value=icon_value, emboss=emboss)
        else:
            pr = self.layout.operator(
                idname, txt, icon=icon, icon_value=icon_value, emboss=emboss)

        if not enabled:
            self.restore()

        self.has_sep = False
        return set_props

    def parse_icon(self, icon):
        icon_value = 0
        if icon.startswith("@"):
            if self.ph:
                icon = icon[1:]
                if self.ph.has_icon(icon):
                    icon_value = self.ph.get_icon(icon)

            icon = 'NONE'

        return icon, icon_value

    def prop(
            self, data, prop, text=None, icon='NONE',
            expand=False, slider=False, toggle=False, icon_only=False,
            event=False, full_event=False, emboss=True, index=-1,
            enabled=True):
        if not hasattr(data, prop):
            raise AttributeError(
                "Property not found: %s.%s" % (type(data).__name__, prop))

        icon, icon_value = self.parse_icon(icon)

        if not enabled:
            self.save()
            scale_x = self.layout.scale_x
            scale_y = self.layout.scale_y
            self.row(enabled=False)
            self.layout.scale_x = scale_x
            self.layout.scale_y = scale_y

        if text is None:
            self.layout.prop(
                data, prop, icon=icon, icon_value=icon_value,
                expand=expand, slider=slider, toggle=toggle,
                icon_only=icon_only, event=event, full_event=full_event,
                emboss=emboss, index=index)
        else:
            self.layout.prop(
                data, prop, text=text, icon=icon, icon_value=icon_value,
                expand=expand, slider=slider, toggle=toggle,
                icon_only=icon_only, event=event, full_event=full_event,
                emboss=emboss, index=index)

        if not enabled:
            self.restore()

        self.has_sep = False

    def restore(self):
        self.layout = self.saved_layouts.pop()

    def row(
            self, parent=None, align=True, operator_context=None,
            enabled=True, alignment='EXPAND'):
        if parent is None:
            parent = self.layout
        self.parent = parent

        self.layout = parent.row(align=align)
        self.layout.alignment = alignment
        self.layout.enabled = enabled
        if operator_context is not None:
            self.layout.operator_context = operator_context

        self.has_sep = True
        return self.layout

    def save(self):
        self.saved_layouts.append(self.layout)

    def sep(self, parent=None, check=False, group=None):
        if parent is None:
            parent = self.layout
        if group and group != self.prev_sep_group or \
                not group and (not check or not self.has_sep):
            parent.separator()
        self.has_sep = True
        self.prev_sep_group = group

    def spacer(self):
        self.layout.operator("wm.pme_none", " ", emboss=False)
        self.has_sep = False

    def split(self, parent=None, percentage=None, align=True):
        if parent is None:
            parent = self.layout
        self.parent = parent

        if percentage is None:
            self.layout = parent.split(align=align)
        else:
            self.layout = parent.split(percentage, align=align)

        self.has_sep = True
        return self.layout

    def unregister(self):
        self.layout = None
        self.saved_layouts = None
        self.ph = None


class Row:
    def __init__(self):
        self.a = 0
        self.b = 0
        self.num_columns = 0

    def __str__(self):
        return "Row [%d, %d] %d cols" % (self.a, self.b, self.num_columns)

    def find_ab(self, pm, idx):
        self.a = idx
        while self.a > 0:
            pmi = pm.pmis[self.a]
            if pmi.mode == 'EMPTY' and pmi.text.startswith('row'):
                break
            self.a -= 1

        self.b = idx + 1
        n = len(pm.pmis)
        while self.b < n:
            pmi = pm.pmis[self.b]
            if pmi.mode == 'EMPTY' and pmi.text.startswith('row'):
                break
            self.b += 1

    def has_columns(self, pm):
        for i in range(self.a + 1, self.b):
            pmi = pm.pmis[i]
            if pmi.mode == 'EMPTY' and pmi.text.startswith("spacer"):
                prop = pme.props.parse(pmi.text)
                if prop.hsep == 'COLUMN':
                    return True

        return False

    def find_columns(self, pm):
        self.num_columns = 0
        for i in range(self.a + 1, self.b):
            pmi = pm.pmis[i]
            if pmi.mode == 'EMPTY':
                prop = pme.props.parse(pmi.text)
                if prop.hsep == 'COLUMN':
                    self.num_columns += 1

        if self.num_columns:
            self.num_columns += 1

    def remove_subrows(self, pm):
        pp = pme.props
        i = self.a + 1
        while i < self.b:
            pmi = pm.pmis[i]  # BUG
            if pmi.mode == 'EMPTY' and pmi.text.startswith("spacer"):
                prop = pp.parse(pmi.text)
                if prop.subrow == 'BEGIN' or prop.subrow == 'END':
                    pmi.text = pp.encode(pmi.text, "subrow", 'NONE')
                    if pp.parse(pmi.text).is_empty:
                        pm.pmis.remove(i)
                        self.b -= 1
                        i -= 1
            i += 1


class Col:
    def __init__(self):
        self.a = 0
        self.b = 0

    def __str__(self):
        return "Col [%d, %d]" % (self.a, self.b)

    @staticmethod
    def is_column(item):
        return item.mode == 'EMPTY' and item.text == "column"

    def calc_num_items(self, pm):
        num_items = self.b - self.a + 1
        if self.a >= len(pm.pmis) or Col.is_column(pm.pmis[self.a]):
            num_items -= 1
        if self.b >= len(pm.pmis) or Col.is_column(pm.pmis[self.b]):
            num_items -= 1
        return num_items

    def find_ab(self, pm, idx):
        if idx == 0:
            self.a = 0
            self.b = 0
            return

        self.a = idx - 1
        while self.a > 0:
            pmi = pm.pmis[self.a]
            if pmi.mode == 'EMPTY' and pmi.text == "column":
                break
            self.a -= 1

        self.b = idx


cur_col = Col()


def draw_pme_layout(pm, column, draw_pmi, rows=None, icon_btn_scale_x=-1):
    global num_btns, num_spacers, max_btns, max_spacers
    pr = prefs()
    pp = pme.props

    if icon_btn_scale_x == -1:
        icon_btn_scale_x = SCALE_X

    num_btns = 0
    num_spacers = 0
    max_btns = 0
    max_spacers = 0

    DBG_LAYOUT and logh("Draw Dialog")

    is_subrow = False
    has_columns = False
    row = None
    row_idx = 0
    last_row_idx = 0
    row_is_expanded = False
    subrow_is_expanded = False
    for idx, pmi in enumerate(pm.pmis):
        if pmi.mode == 'EMPTY':
            if row and pmi.text.startswith("row"):
                row_prop = pp.parse(pm.pmis[row_idx].text)
                if not row_is_expanded:
                    row.alignment = row_prop.align
                row_is_expanded = False

                if is_subrow and not subrow_is_expanded:
                    cur_subrow.alignment = row_prop.align
                subrow_is_expanded = False

                last_row_idx = row_idx
                row_idx = idx

            if pmi.text.startswith("spacer"):
                prop = pp.parse(pmi.text)
                if prop.subrow == 'BEGIN' or prop.subrow == 'END' or \
                        prop.hsep == 'COLUMN':
                    if is_subrow and not subrow_is_expanded:
                        row_prop = pp.parse(pm.pmis[row_idx].text)
                        cur_subrow.alignment = row_prop.align
                    subrow_is_expanded = False

            has_columns_mem = has_columns
            new_row, has_columns, is_subrow = _parse_empty_pdi(
                pr, pm, idx, row_idx, column, row, has_columns, is_subrow)
            if not new_row:
                new_row = row

            if rows is not None and pmi.text.startswith("row") and row:
                row_prop = pp.parse(pm.pmis[last_row_idx].text)
                rows.append((
                    last_row_idx, row_prop.value("size"),
                    max_btns, max_spacers, has_columns_mem,
                    row_prop.value("vspacer")))
                max_btns = 0
                max_spacers = 0

            row = new_row

            continue

        text, icon, _, _, _ = pmi.parse()
        row_prop = pp.parse(pm.pmis[row_idx].text)

        if not is_subrow and has_columns:
            lh.save()
            subrow = lh.row()
            subrow.scale_x = pr.button_scalex
            subrow.scale_y = 1  # row_prop.value("size")

            if pmi.mode == 'PROP':
                if not pmi.is_expandable_prop() and not text:
                    subrow.alignment = row_prop.align
            elif not text:
                subrow.alignment = row_prop.align

        lh.save()
        item_col = lh.column()

        scale_x = 1
        scale_y = row_prop.value("size")
        if not text:
            if pmi.mode == 'PROP':
                bl_prop = bp.get(pmi.text)
                if not bl_prop or bl_prop.type == 'BOOLEAN':
                    scale_x = max(icon_btn_scale_x, scale_y)
            else:
                scale_x = max(icon_btn_scale_x, scale_y)

        item_col.scale_x = scale_x
        item_col.scale_y = scale_y

        draw_pmi(pr, pm, pmi, idx)

        lh.restore()

        if not is_subrow and has_columns:
            lh.restore()

        DBG_LAYOUT and logi("PDI")
        if not is_subrow:
            num_btns += 1

        if not row_is_expanded:
            if pmi.name and (icon == 'NONE' or "#" not in pmi.icon):
                row_is_expanded = True
            elif pmi.is_expandable_prop():
                row_is_expanded = True
            # elif pmi.mode == 'CUSTOM' and is_expandable(pmi.text):
            #     row_is_expanded = True

        if is_subrow:
            if not subrow_is_expanded:
                if pmi.name and (icon == 'NONE' or "#" not in pmi.icon):
                    subrow_is_expanded = True
                elif pmi.is_expandable_prop():
                    subrow_is_expanded = True
                # elif pmi.mode == 'CUSTOM' and is_expandable(pmi.text):
                #     subrow_is_expanded = True

    if row:
        row_prop = pp.parse(pm.pmis[row_idx].text)
        if not row_is_expanded:
            row.alignment = row_prop.align
        if is_subrow and not subrow_is_expanded:
            cur_subrow.alignment = row_prop.align

        size = row_prop.value("size")
        if max_btns * size + max_spacers * SPACER_SCALE_Y < \
                num_btns * size + num_spacers * SPACER_SCALE_Y:
            max_btns = num_btns if has_columns else 1
            max_spacers = num_spacers if has_columns else 0
        if rows is not None:
            rows.append((
                row_idx, row_prop.value("size"), max_btns, max_spacers,
                has_columns, row_prop.value("vspacer")))

    pme.context.is_first_draw = False

    return rows

cur_column = None
cur_subrow = None
prev_row_has_columns = False
num_btns = 0
num_spacers = 0
max_btns = 0
max_spacers = 0


def _parse_empty_pdi(
        prefs, pm, idx, row_idx, layout, row, has_columns, is_subrow):
    global cur_column, cur_subrow, \
        num_btns, num_spacers, max_btns, max_spacers
    pp = pme.props
    pmi = pm.pmis[idx]
    r = pp.parse(pmi.text)
    DBG_LAYOUT and logi(pmi.text)

    if pmi.text.startswith("row"):
        if row and r.vspacer != 'NONE':
            lh.lt(layout)
            for i in range(0, r.value("vspacer")):
                lh.sep()

        row_prop = pp.parse(pm.pmis[row_idx].text)
        size = row_prop.value("size")
        if max_btns * size + max_spacers * SPACER_SCALE_Y < \
                num_btns * size + num_spacers * SPACER_SCALE_Y:
            max_btns = num_btns if has_columns else 1
            max_spacers = num_spacers if has_columns else 0
        num_btns = 0
        num_spacers = 0

        has_columns = False
        while idx < len(pm.pmis) - 1:
            idx += 1
            next_pmi = pm.pmis[idx]
            if next_pmi.mode == 'EMPTY':
                if next_pmi.text.startswith("row"):
                    break
                prop = pp.parse(next_pmi.text)
                if prop.hsep == 'COLUMN':
                    has_columns = True
                    break

        if has_columns and row_prop.fixed_col:
            row = lh.split(layout, align=False)
        else:
            row = lh.row(layout, align=not has_columns)
        row.scale_x = prefs.button_scalex
        row.scale_y = 1  # r.value("size")
        row.alignment = 'EXPAND'
        is_subrow = False
        if has_columns:
            row.scale_x = 1
            row.scale_y = 1
            column = lh.column()
            cur_column = column

        return row, has_columns, is_subrow

    elif pmi.text.startswith("spacer"):
        if r.subrow == 'END' or is_subrow and r.subrow == 'BEGIN':
            lh.lt(cur_column)
            is_subrow = False

        if r.hsep == 'SPACER':
            if not is_subrow:
                num_spacers += 1
            lh.sep()
        elif r.hsep == 'LARGE':
            lh.sep()
            lh.blank()
            lh.sep()
        elif r.hsep == 'LARGER':
            lh.sep()
            lh.spacer()
            lh.sep()
        elif r.hsep == 'COLUMN':
            lh.lt(row)
            # lh.sep()
            row.scale_x = 1
            row.scale_y = 1
            column = lh.column(row)
            cur_column = column

            if max_btns < num_btns:
                max_btns = num_btns if has_columns else 1
                max_spacers = num_spacers if has_columns else 0
            num_btns = 0
            num_spacers = 0
            is_subrow = False

        if r.subrow == 'BEGIN':
            subrow = lh.row(cur_column)

            row_prop = pp.parse(pm.pmis[row_idx].text)
            subrow.scale_x = prefs.button_scalex
            subrow.scale_y = 1  # row_prop.value("size")
            num_btns += 1
            is_subrow = True
            cur_subrow = subrow

    return None, has_columns, is_subrow


lh = LayoutHelper(ph)


def register():
    pme.context.add_global("lh", lh)
