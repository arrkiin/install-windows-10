import bpy
import traceback
from .debug_utils import *
from . import operator_utils
from .bl_utils import bp

uilayout_getattribute = bpy.types.UILayout.__getattribute__
draw_addons_default = None


def utitle(text):
    words = [word[0].upper() + word[1:] for word in text.split("_") if word]
    return " ".join(words)


def shorten_str(value, n=50):
    return value[:n] + (value[n:] and "...")


def find_enum_args(mo):
    args = mo.group(2)[1:-1]
    args = args.split(",")
    args = [arg.split("=")[0].strip() for arg in args]
    if not args:
        return False

    enum_args = []

    try:
        tp_name = eval("bpy.ops.%s.idname()" % mo.group(1))
        tp = getattr(bpy.types, tp_name)
        properties = tp.bl_rna.properties
        for arg in args:
            if arg in properties:
                if properties[arg].type == 'ENUM':
                    enum_args.append(arg)
            elif hasattr(tp, arg):
                if 'Enum' in getattr(tp, arg)[0]:
                    enum_args.append(arg)

    except:
        pass

    return enum_args


def gen_op_name(mo, strict=False):
    try:
        op_type_name = eval("bpy.ops.%s.idname()" % mo.group(1))
        op_type = getattr(bpy.types, op_type_name)
        name = operator_utils.get_op_label(op_type)
    except:
        name = "" if strict else shorten_str(mo.group(1) + mo.group(2))

    return name


def gen_prop_name(mo, is_prop=False, strict=False):
    name = mo.group(2)

    if not is_prop:
        name += mo.group(3)
    name = "" if strict else shorten_str(name)
    icon = ""

    prop_path = mo.group(1) + mo.group(2)

    if is_prop and prop_path[-1] == "]":
        prop_path, _, _ = prop_path.rpartition("[")

    prop = bp.get(prop_path)

    if prop:
        name = prop.name
        icon = prop.icon
        if not is_prop:
            name += mo.group(3)

    return name, icon


def tag_redraw(all=False):
    wm = bpy.context.window_manager
    if not wm:
        return

    for w in wm.windows:
        for a in w.screen.areas:
            if all or a.type == 'USER_PREFERENCES':
                for r in a.regions:
                    if all or r.type == 'WINDOW':
                        r.tag_redraw()


def find_area(area_type):
    for s in bpy.data.screens:
        for a in s.areas:
            if a.type == area_type:
                return a
    return None


def find_space(space_type):
    for s in bpy.data.screens:
        for a in s.areas:
            for sp in a.spaces:
                if sp.type == space_type:
                    return sp
    return None


def draw_addons_maximized(self, context):
    layout = self.layout

    if PME_OT_userpref_show.mod != "pie_menu_editor":
        row = self.layout.row(True)
        row.scale_y = 1.5
        row.operator(PME_OT_userpref_restore.bl_idname, "Restore")

    prefs = context.user_preferences.addons[
        PME_OT_userpref_show.mod].preferences

    draw = getattr(prefs, "draw", None)
    prefs_class = type(prefs)
    layout = layout.box()
    prefs_class.layout = layout
    try:
        draw(context)
    except:
        DBG and loge(traceback.format_exc())
        layout.label(text="Error (see console)", icon='ERROR')
    del prefs_class.layout


class PME_OT_userpref_show(bpy.types.Operator):
    bl_idname = "pme.userpref_show"
    bl_label = "User Preferences"
    bl_options = {'INTERNAL'}

    mod = None

    tab = bpy.props.StringProperty(options={'SKIP_SAVE'})
    addon = bpy.props.StringProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        if context.area.type != 'USER_PREFERENCES':
            bpy.ops.screen.userpref_show('INVOKE_DEFAULT')

        if self.addon:
            PME_OT_userpref_show.mod = self.addon
            bpy.types.USERPREF_PT_addons.draw = draw_addons_maximized
            self.tab = 'ADDONS'

        else:
            bpy.types.USERPREF_PT_addons.draw = draw_addons_default

        if self.tab:
            context.user_preferences.active_section = self.tab
        tag_redraw()
        return {'FINISHED'}


class PME_OT_userpref_restore(bpy.types.Operator):
    bl_idname = "pme.userpref_restore"
    bl_label = "Restore User Preferences Area"

    def execute(self, context):
        bpy.types.USERPREF_PT_addons.draw = draw_addons_default
        return {'FINISHED'}


def pme_uilayout_getattribute(self, attr):
    def pme_operator(
            operator, text="",
            text_ctxt="", translate=True, icon='NONE',
            emboss=True, icon_value=0):
        uilayout_operator = uilayout_getattribute(self, "operator")

        return uilayout_operator(
            operator, text,
            text_ctxt, translate, icon, emboss, icon_value)

    if attr == "operator":
        return pme_operator

    return uilayout_getattribute(self, attr)


def is_userpref_maximized():
    return bpy.types.USERPREF_PT_addons.draw == draw_addons_maximized


def register():
    # bpy.types.UILayout.__getattribute__ = pme_uilayout_getattribute
    global draw_addons_default
    draw_addons_default = bpy.types.USERPREF_PT_addons.draw


def unregister():
    # bpy.types.UILayout.__getattribute__ = uilayout_getattribute
    if bpy.types.USERPREF_PT_addons.draw != draw_addons_default:
        bpy.types.USERPREF_PT_addons.draw = draw_addons_default
