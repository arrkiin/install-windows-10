bl_info = {
    "name": "Pie Menu Editor",
    "author": "roaoao",
    "version": (1, 13, 3),
    "blender": (2, 75, 0),
    "warning": "",
    "tracker_url": "http://blenderartists.org/forum/showthread.php?392910",
    "wiki_url": (
        "https://wiki.blender.org/index.php/User:Raa/Addons/Pie_Menu_Editor"),
    "category": "User Interface"
}


import bpy
from bpy.app.handlers import persistent
import sys

if not bpy.app.background:
    MODULES = (
        "addon",
        "constants",
        "debug_utils",
        "property_utils",
        "operator_utils",
        "overlay",
        "selection_state",
        "previews_helper",
        "pme",
        "bl_utils",
        "macro_utils",
        "panel_utils",
        "keymap_helper",
        "layout_helper",
        "ui",
        "operators",
        "extra_operators",
        "ui_utils",
        "ed_base",
        "ed_pie_menu",
        "ed_menu",
        "ed_popup",
        "ed_stack_key",
        "ed_sticky_key",
        "ed_macro",
        "ed_panel_group",
        "ed_hpanel_group",
        "preferences",
    )

    import importlib
    for mod in MODULES:
        if mod in locals():
            try:
                importlib.reload(locals()[mod])
                continue
            except:
                pass

        importlib.import_module("pie_menu_editor." + mod)

    from .addon import prefs
    from .debug_utils import *
    from . import property_utils
    from .overlay import Timer
    from . import pme

tmp_data = None
re_enable_data = None
tmp_filepath = None


@persistent
def load_pre_handler(_):
    DBG and logh("Load Pre")
    global tmp_data
    tmp_data = property_utils.to_dict(prefs())

    global tmp_filepath
    tmp_filepath = bpy.data.filepath
    if not tmp_filepath:
        tmp_filepath = "__unsaved__"


@persistent
def load_post_handler(_):
    DBG and logh("Load Post")
    global tmp_data
    if tmp_data is None:
        return

    if not bpy.data.filepath:
        property_utils.from_dict(prefs(), tmp_data)

    tmp_data = None

    prefs().tree.update()


@persistent
def wait_context(_):
    bpy.app.handlers.scene_update_post.remove(wait_context)
    pme.context.add_global("C", bpy.context)
    pme.context.add_global("D", bpy.data)
    pme.context.add_global("T", bpy.types)
    pme.context.add_global("O", bpy.ops)
    pme.context.add_global("P", bpy.props)
    pme.context.add_global("bpy", bpy)
    pme.context.add_global("sys", sys)
    pme.context.add_global("BoolProperty", bpy.props.BoolProperty)
    pme.context.add_global("IntProperty", bpy.props.IntProperty)
    pme.context.add_global("FloatProperty", bpy.props.FloatProperty)
    pme.context.add_global("StringProperty", bpy.props.StringProperty)
    pme.context.add_global("EnumProperty", bpy.props.EnumProperty)
    pme.context.add_global("CollectionProperty", bpy.props.CollectionProperty)
    pme.context.add_global("PointerProperty", bpy.props.PointerProperty)
    pme.context.add_global(
        "FloatVectorProperty", bpy.props.FloatVectorProperty)

    for k, v in globals().items():
        if k.startswith("__"):
            pme.context.add_global(k, v)


@persistent
def wait_keymaps(_):
    DBG and logh("Wait Keymaps")

    pr = prefs()

    keymaps = bpy.context.window_manager.keyconfigs.user.keymaps
    kms_to_remove = []
    for km in pr.missing_kms.keys():
        if km in keymaps:
            kms_to_remove.append(km)

    if kms_to_remove:
        for km in kms_to_remove:
            pm_names = pr.missing_kms[km]
            for pm_name in pm_names:
                pr.pie_menus[pm_name].register_hotkey()
            pr.missing_kms.pop(km, None)

    if not pr.missing_kms or bpy.pme_timer.update():
        del bpy.pme_timer
        bpy.app.handlers.scene_update_post.remove(wait_keymaps)


@persistent
def wait_addons(_):
    bpy.app.handlers.scene_update_post.remove(wait_addons)

    bpy.utils.register_module(__name__)
    pr = prefs()

    global re_enable_data
    if re_enable_data is not None:
        if len(pr.pie_menus) == 0 and re_enable_data:
            property_utils.from_dict(pr, re_enable_data)
        re_enable_data.clear()
        re_enable_data = None

    for mod in MODULES:
        m = sys.modules["%s.%s" % (__name__, mod)]
        if hasattr(m, "register"):
            m.register()

    if pr.missing_kms:
        bpy.pme_timer = Timer(10)
        bpy.app.handlers.scene_update_post.append(wait_keymaps)

    bpy.app.handlers.scene_update_post.append(wait_context)

    bpy.app.handlers.load_pre.append(load_pre_handler)
    bpy.app.handlers.load_post.append(load_post_handler)


def register():
    if bpy.app.background:
        return

    DBG and logh("PME Register")

    bpy.app.handlers.scene_update_post.append(wait_addons)


def unregister():
    if bpy.app.background:
        return

    DBG and logh("PME Unregister")

    global re_enable_data
    re_enable_data = property_utils.to_dict(prefs())

    for mod in reversed(MODULES):
        m = sys.modules["%s.%s" % (__name__, mod)]
        if hasattr(m, "unregister"):
            m.unregister()

    if hasattr(bpy.types.WindowManager, "pme"):
        delattr(bpy.types.WindowManager, "pme")

    if wait_addons in bpy.app.handlers.scene_update_post:
        bpy.app.handlers.scene_update_post.remove(wait_addons)

    if wait_keymaps in bpy.app.handlers.scene_update_post:
        bpy.app.handlers.scene_update_post.remove(wait_keymaps)

    bpy.app.handlers.load_pre.remove(load_pre_handler)
    bpy.app.handlers.load_post.remove(load_post_handler)

    bpy.utils.unregister_module(__name__)
