import bpy
import re
from . import pme

re_operator = re.compile(r"^(?:bpy\.ops|O)\.(\w+\.\w+)(\(.*)")
re_prop = re.compile(r"^(.*?)([^.\s]+\.[^.\s]+)(\s*=\s*(.*))")
re_prop_set = re.compile(r"^(.*?)([^.\s]+\.[^.\s]+)(\s*=\s*(.*))?$")
re_name_idx = re.compile(r"^(.*)\.(\d+)$")
re_icon = re.compile(r"^([A-Z]*_).*")


def _add_options(kwargs):
    if "options" not in kwargs:
        kwargs["options"] = {'SKIP_SAVE'}
    return kwargs


def pbool(**kwargs):
    return bpy.props.BoolProperty(**_add_options(kwargs))


def pint(**kwargs):
    return bpy.props.IntProperty(**_add_options(kwargs))


def pfloat(**kwargs):
    return bpy.props.FloatProperty(**_add_options(kwargs))


def pstring(**kwargs):
    return bpy.props.StringProperty(**_add_options(kwargs))


def penum(**kwargs):
    return bpy.props.EnumProperty(**_add_options(kwargs))


def pcoll(**kwargs):
    return bpy.props.CollectionProperty(**_add_options(kwargs))


def ppointer(**kwargs):
    return bpy.props.PointerProperty(**_add_options(kwargs))


def find_context(area_type):
    area = None
    for a in bpy.context.screen.areas:
        if a.type == area_type:
            area = a
            break

    if not area:
        return None

    return {
        "area": area,
        "window": bpy.context.window,
        "screen": bpy.context.screen
    }


def paint_settings(context):
    if context.space_data and context.space_data.type == 'IMAGE_EDITOR':
        return context.tool_settings.image_paint
    else:
        return bpy.types.VIEW3D_PT_tools_brush.paint_settings(context)


class BlContext(bpy.types.Context):
    context = None
    area = None
    region = None
    space_data = None

    mods = dict(
        fracture='FRACTURE',
        cloth='CLOTH',
        dynamic_paint='DYNAMIC_PAINT',
        smoke='SMOKE',
        fluid='FLUID_SIMULATION',
        collision='COLLISION',
        soft_body='SOFT_BODY',
        particle_system='PARTICLE_SYSTEM',
    )

    data = {
        "armature",
        "camera",
        "curve",
        "lamp",
        "lattice",
        "mesh",
        "meta_ball",
        "speaker",
    }

    def get_modifier_by_type(self, ao, tp):
        if not ao or not hasattr(ao, "modifiers"):
            return None

        for mod in ao.modifiers:
            if mod.type == tp:
                return mod

    def __getattr__(self, attr):
        if not BlContext.context:
            BlContext.context = bpy.context

        value = None
        if hasattr(BlContext.context, attr):
            value = getattr(BlContext.context, attr)

        ao = BlContext.context.active_object

        if not value:
            if attr == "region":
                value = BlContext.region
            elif attr == "space_data":
                value = BlContext.space_data
            elif attr == "area":
                value = BlContext.area
            elif attr == "material_slot":
                value = ao and ao.material_slots[ao.active_material_index]
            elif attr == "material":
                value = ao and ao.active_material
            elif attr == "world":
                value = hasattr(BlContext.context, "scene") and \
                    BlContext.context.scene.world
            elif attr == "brush":
                ps = paint_settings(BlContext.context)
                value = ps.brush if ps and hasattr(ps, "brush") else None
            elif attr == "bone":
                value = None
            elif attr == "edit_bone":
                value = None
            elif attr == "texture":
                value = None
            elif attr == "line_style":
                value = None
            elif attr in BlContext.data:
                value = ao.data if ao else None
            elif attr == "particle_system":
                if len(ao.particle_systems):
                    value = ao.particle_systems[
                        ao.particle_systems.active_index]
                else:
                    value = None
            elif attr in BlContext.mods:
                value = self.get_modifier_by_type(ao, BlContext.mods[attr])

        return value

    def set_context(self, context):
        BlContext.context = context

    def reset(self, context):
        BlContext.area = context.area
        BlContext.region = context.region
        BlContext.space_data = context.space_data


bl_context = BlContext(bpy.context.window_manager)


class BlProp:
    def __init__(self):
        self.data = {}

    def get(self, text):
        prop = None
        if text in self.data:
            try:
                prop = eval(self.data[text])
            except:
                pass
            return prop

        obj, _, prop_name = text.rpartition(".")

        co = None
        try:
            text = "%s.bl_rna.properties['%s']" % (obj, prop_name)
            co = compile(text, '<string>', 'eval')
        except:
            pass

        if co:
            self.data[text] = co
            try:
                prop = eval(co)
            except:
                pass
            return prop

        return None


bp = BlProp()


class MoveItemOperator:
    label_prop = "name"
    bl_idname = None
    bl_label = "Move Item"
    bl_description = "Move the item"
    bl_options = {'INTERNAL'}

    old_idx = bpy.props.IntProperty(default=-1, options={'SKIP_SAVE'})
    new_idx = bpy.props.IntProperty(default=-1, options={'SKIP_SAVE'})
    swap = bpy.props.BoolProperty(options={'SKIP_SAVE'})
    title = bpy.props.StringProperty(
        default="Move Item", options={'SKIP_SAVE'})
    icon = bpy.props.StringProperty(options={'SKIP_SAVE'})

    def get_collection(self):
        return None

    def draw_menu(self, menu, context):
        layout = menu.layout
        collection = self.get_collection()

        for i, item in enumerate(collection):
            name = getattr(item, self.label_prop)
            icon = 'SPACE2' if i == self.old_idx else 'SPACE3'

            p = layout.operator(self.bl_idname, name, icon=icon)
            p.swap = self.swap
            p.old_idx = self.old_idx
            p.new_idx = i

    def finish(self):
        pass

    def execute(self, context):
        collection = self.get_collection()
        if self.old_idx < 0 or self.old_idx >= len(collection):
            return {'CANCELLED'}

        if self.new_idx == -1:
            icon = self.icon
            if not icon:
                icon = 'ARROW_LEFTRIGHT' if self.swap else 'FORWARD'
            bpy.context.window_manager.popup_menu(
                self.draw_menu, self.title or self.bl_label, icon)
            return {'FINISHED'}

        if self.new_idx < 0 or self.new_idx >= len(collection):
            return {'CANCELLED'}

        if self.new_idx != self.old_idx:
            collection.move(self.old_idx, self.new_idx)

            if self.swap:
                swap_idx = self.new_idx - 1 \
                    if self.old_idx < self.new_idx \
                    else self.new_idx + 1
                if swap_idx != self.old_idx:
                    collection.move(swap_idx, self.old_idx)

            self.finish()

        return {'FINISHED'}


class RemoveItemOperator:
    bl_label = "Remove Item"
    bl_description = "Remove the item"
    bl_options = {'INTERNAL'}

    idx = bpy.props.IntProperty(options={'SKIP_SAVE'})

    def get_collection(self):
        return None

    def finish(self):
        pass

    def execute(self, context):
        collection = self.get_collection()
        if self.idx < 0 or self.idx >= len(collection):
            return {'CANCELLED'}

        collection.remove(self.idx)

        self.finish()
        return {'FINISHED'}


class AddItemOperator:
    bl_label = "Add Item"
    bl_description = "Add an item"
    bl_options = {'INTERNAL'}

    idx = bpy.props.IntProperty(default=-1, options={'SKIP_SAVE'})

    def get_collection(self):
        return None

    def finish(self, item):
        pass

    def execute(self, context):
        collection = self.get_collection()
        item = collection.add()

        idx = len(collection) - 1
        if 0 <= self.idx < idx:
            collection.move(idx, self.idx)
            item = collection[self.idx]

        self.finish(item)
        return {'FINISHED'}


class BaseCollectionItem(bpy.types.PropertyGroup):
    pass


def register():
    pme.context.add_global("bl_context", bl_context)
    pme.context.add_global("paint_settings", paint_settings)
    pme.context.add_global("re", re)
