import bpy
import traceback
from uuid import uuid4
from types import MethodType
from .bl_utils import bl_context
from .debug_utils import *
from . import pme


_hidden_panels = {}
_panels = {}
_context_items = []
_bl_panel_types = []


def hide_panel(tp_name):
    if tp_name in _hidden_panels:
        pass

    elif hasattr(bpy.types, tp_name):
        tp = getattr(bpy.types, tp_name)
        bpy.utils.unregister_class(tp)
        _hidden_panels[tp_name] = tp


def unhide_panel(tp_name):
    if tp_name in _hidden_panels:
        bpy.utils.register_class(_hidden_panels[tp_name])
        del _hidden_panels[tp_name]

    else:
        pass


def hidden_panel(tp_name):
    if tp_name in _hidden_panels:
        return _hidden_panels[tp_name]

    return None


def is_panel_hidden(tp_name):
    return tp_name in _hidden_panels


def get_hidden_panels():
    return _hidden_panels


def add_panel(
        name, idx, id, label, space, region,
        context=None, category=None, draw=None, poll=None):
    if name not in _panels:
        _panels[name] = []

    if not label:
        label = "PME Panel"

    tp_name = "PME_PT_%s" % uuid4().hex
    defs = {
        "bl_label": label,
        "bl_space_type": space,
        "bl_region_type": region,
        "pm_name": name,
        "pme_data": id,
        "draw": draw,
        "poll": classmethod(poll)
    }
    if context and context != 'ANY':
        defs["bl_context"] = context
    if category:
        defs["bl_category"] = category

    base = bpy.types.Header if region == 'HEADER' else bpy.types.Panel

    tp = type(tp_name, (base,), defs)

    try:
        bpy.utils.register_class(tp)
        _panels[name].insert(idx, tp)
    except:
        pass


def remove_panel(name, idx):
    if name not in _panels or idx >= len(_panels[name]):
        return

    bpy.utils.unregister_class(_panels[name][idx])
    _panels[name].pop(idx)


def remove_panel_group(name):
    if name not in _panels:
        return

    for panel in _panels[name]:
        bpy.utils.unregister_class(panel)

    del _panels[name]


def refresh_panel_group(name):
    if name not in _panels:
        return

    for panel in _panels[name]:
        bpy.utils.unregister_class(panel)

    for panel in _panels[name]:
        bpy.utils.register_class(panel)


def rename_panel_group(old_name, name):
    if old_name not in _panels:
        return

    for panel in _panels[old_name]:
        panel.pm_name = name

    _panels[name] = _panels[old_name]
    del _panels[old_name]


def move_panel(name, old_idx, idx):
    if name not in _panels or old_idx == idx or \
            old_idx >= len(_panels[name]) or idx > len(_panels[name]):
        return

    panels = _panels[name]
    panel = panels.pop(old_idx)
    panels.insert(idx, panel)

    # refresh_panel_group(name)


def panel_context_items(self, context):
    if not _context_items:
        _context_items.append(('ANY', "Any Context", "", 'NODE_SEL', 0))
        panel_tp = bpy.types.Panel
        contexts = set()
        for tp_name in dir(bpy.types):
            tp = getattr(bpy.types, tp_name)
            if tp == panel_tp or not issubclass(tp, panel_tp) or \
                    not hasattr(tp, "bl_context"):
                continue

            contexts.add(tp.bl_context)

        idx = 1
        for ctx in sorted(contexts):
            _context_items.append(
                (ctx, ctx.replace("_", " ").title(), "", 'NODE', idx))
            idx += 1

    return _context_items


def bl_panel_types():
    ret = []
    panel_tp = bpy.types.Panel
    for tp_name in dir(bpy.types):
        tp = getattr(bpy.types, tp_name)
        if tp == panel_tp or not issubclass(tp, panel_tp) or \
                hasattr(tp, "pme_data"):
            continue

        ret.append(tp)

    for tp in _hidden_panels.values():
        ret.append(tp)

    return ret


class PME_OT_panel_toggle(bpy.types.Operator):
    bl_idname = "pme.panel_toggle"
    bl_label = ""
    bl_description = "Show/hide the panel"
    bl_options = {'INTERNAL'}

    collapsed_panels = set()

    panel_id = bpy.props.StringProperty()

    def execute(self, context):
        if self.panel_id in self.__class__.collapsed_panels:
            self.__class__.collapsed_panels.remove(self.panel_id)
        else:
            self.__class__.collapsed_panels.add(self.panel_id)
        return {'FINISHED'}


def panel(pt, frame=True, header=True, expand=None, root=False, **kwargs):
    DBG and logh("Panel")
    bl_context.set_context(bpy.context)
    context_class = type(bpy.context)
    for k, v in kwargs.items():
        setattr(context_class, k, v)

    space_data = bl_context.space_data
    if space_data:
        space_class = type(space_data)
        setattr(space_class, "use_pin_id", None)
        setattr(space_class, "pin_id", None)

    def restore_types():
        for k in kwargs.keys():
            delattr(context_class, k)

        if space_data:
            delattr(space_class, "use_pin_id")
            delattr(space_class, "pin_id")

    try:
        if "tabs_interface" in bpy.context.user_preferences.addons:
            import tabs_interface
            tabs_interface.USE_DEFAULT_POLL = True

        if hasattr(pt, "poll") and not pt.poll(bl_context):
            restore_types()
            return

        if "tabs_interface" in bpy.context.user_preferences.addons:
            tabs_interface.USE_DEFAULT_POLL = False

    except:
        DBG and logi(traceback.format_exc())
        restore_types()
        return

    p = pt(bpy.context.window_manager)
    if root:
        layout = pme.context.layout
    else:
        layout = pme.context.layout.box() if frame else \
            pme.context.layout.column()

    is_collapsed = False

    if header:
        row = layout.row(True)
        row.alignment = 'LEFT'
        item_id = pme.context.item_id()
        try:
            if expand is not None and pme.context.is_first_draw:
                if expand:
                    if item_id in PME_OT_panel_toggle.collapsed_panels:
                        PME_OT_panel_toggle.collapsed_panels.remove(item_id)
                else:
                    PME_OT_panel_toggle.collapsed_panels.add(item_id)
        except:
            traceback.print_exc()

        is_collapsed = item_id in PME_OT_panel_toggle.collapsed_panels
        icon = 'TRIA_RIGHT' if is_collapsed else 'TRIA_DOWN'
        row.operator(
            PME_OT_panel_toggle.bl_idname, "",
            icon=icon, emboss=False).panel_id = item_id
        if hasattr(p, "draw_header"):
            p.layout = row
            if isinstance(p.draw_header, MethodType):
                p.draw_header(bl_context)
            else:
                p.draw_header(p, bl_context)
        row.operator(
            PME_OT_panel_toggle.bl_idname, pme.context.pmi.name,
            emboss=False).panel_id = item_id

    if not is_collapsed:
        p.layout = layout if root else layout.column()
        try:
            if hasattr(p, "draw"):
                if isinstance(p.draw, MethodType):
                    p.draw(bl_context)
                else:
                    p.draw(p, bl_context)
        except:
            DBG and logi(traceback.format_exc())

    restore_types()


def register():
    pme.context.add_global("panel", panel)


def unregister():
    for v in _hidden_panels.values():
        bpy.utils.register_class(v)

    _hidden_panels.clear()

    for panels in _panels.values():
        for panel in panels:
            bpy.utils.unregister_class(panel)

    _panels.clear()
