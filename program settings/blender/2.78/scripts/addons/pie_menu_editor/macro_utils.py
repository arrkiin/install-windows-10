import bpy
import re
from traceback import print_exc
from uuid import uuid4
from . import operator_utils
from .debug_utils import *
from .addon import prefs


_macros = {}
_macro_execs = []
_exec_base = None
_sticky = None


def init_macros(exec1, base, sticky):
    _macro_execs.append(exec1)
    global _exec_base, _sticky
    _exec_base = base
    _sticky = sticky


def add_macro_exec():
    id = "macro_exec%d" % (len(_macro_execs) + 1)
    tp_name = "PME_OT_" + id
    defs = {
        "bl_idname": "pme." + id,
    }

    tp = type(tp_name, (_exec_base, bpy.types.Operator), defs)

    bpy.utils.register_class(tp)
    _macro_execs.append(tp)


def _gen_tp_id(name):
    def repl(mo):
        c =  mo.group(0)
        try:
            cc = ord(c)
        except:
            return "_"
        return chr(97 + cc % 26)
    name = name.replace(" ", "_")
    id = "macro_" + re.sub(r"[^_a-z0-9]", repl, name, flags=re.I)
    return "PME_OT_" + id, "pme." + id


def add_macro(pm):
    if pm.name in _macros:
        return

    pr = prefs()
    tp_name, tp_bl_idname = _gen_tp_id(pm.name)

    DBG_MACRO and logh("Add Macro: %s (%s)" % (pm.name, tp_name))

    defs = {
        "bl_label": pm.name,
        "bl_idname": tp_bl_idname,
        "bl_options": {'REGISTER', 'UNDO'}
    }

    tp = type(tp_name, (bpy.types.Macro,), defs)

    try:
        bpy.utils.register_class(tp)
        _macros[pm.name] = tp

        idx = 1
        for pmi in pm.pmis:
            pmi.icon = ''
            if pmi.mode == 'COMMAND':
                sub_op_idname, _, _ = operator_utils.find_operator(pmi.text)

                if sub_op_idname:
                    sub_tp = eval("bpy.ops." + sub_op_idname).idname()
                    pmi.icon = 'BLENDER'
                    DBG_MACRO and logi("Type", sub_tp)
                    tp.define(sub_tp)
                else:
                    while len(_macro_execs) < idx:
                        add_macro_exec()
                    pmi.icon = 'TEXT'
                    DBG_MACRO and logi("Command", pmi.text)
                    tp.define("PME_OT_macro_exec%d" % idx)
                    idx += 1

            elif pmi.mode == 'MENU':
                if pmi.text not in pr.pie_menus:
                    continue
                sub_pm = pr.pie_menus[pmi.text]
                if sub_pm.mode == 'MACRO':
                    sub_tp = _macros.get(sub_pm.name, None)
                    if sub_tp:
                        DBG_MACRO and logi("Macro", sub_pm.name)
                        tp.define(sub_tp.__name__)
                elif sub_pm.mode == 'STICKY':
                    DBG_MACRO and logi("Sticky", sub_pm.name)
                    tp.define(_sticky.__name__)

    except:
        print_exc()


def remove_macro(pm):
    if pm.name not in _macros:
        return

    bpy.utils.unregister_class(_macros[pm.name])
    del _macros[pm.name]


def remove_all_macros():
    for v in _macros.values():
        bpy.utils.unregister_class(v)
    _macros.clear()

    while len(_macro_execs) > 1:
        bpy.utils.unregister_class(_macro_execs.pop())
    _macro_execs.clear()


def update_macro(pm):
    if pm.name not in _macros:
        return

    remove_macro(pm)
    add_macro(pm)


def _fill_props(props, pm, idx=1):
    pr = prefs()

    for pmi in pm.pmis:
        if pmi.mode == 'COMMAND':
            sub_op_idname, args, _ = operator_utils.find_operator(pmi.text)

            if sub_op_idname:
                args = ",".join(args)
                sub_tp = eval("bpy.ops." + sub_op_idname).idname()

                props[sub_tp] = eval("dict(%s)" % args)
            else:
                # while len(_macro_execs) < idx:
                #     add_macro_exec()
                props["PME_OT_macro_exec%d" % idx] = dict(cmd=pmi.text)
                idx += 1

        elif pmi.mode == 'MENU':
            sub_pm = pr.pie_menus[pmi.text]
            if sub_pm.mode == 'STICKY':
                props["PME_OT_sticky_key"] = dict(pm_name=sub_pm.name)
            elif sub_pm.mode == 'MACRO':
                sub_props = {}
                _fill_props(sub_props, sub_pm)
                props[_macros[sub_pm.name].__name__] = sub_props


def execute_macro(pm):
    if pm.name not in _macros:
        return

    tp = _macros[pm.name]
    op = eval("bpy.ops." + tp.bl_idname)
    props = {}
    _fill_props(props, pm)
    op('INVOKE_DEFAULT', **props)


def rename_macro(old_name, name):
    if old_name not in _macros:
        return

    _macros[name] = _macros[old_name]
    _macros[name].bl_label = name
    del _macros[old_name]

    bpy.utils.unregister_class(_macros[name])

    tp_name, tp_bl_idname = _gen_tp_id(name)
    _macros[name].__name__ = tp_name
    _macros[name].bl_idname = tp_bl_idname
    bpy.utils.register_class(_macros[name])


def register():
    pass


def unregister():
    remove_all_macros()
