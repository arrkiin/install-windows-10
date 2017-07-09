import bpy
import traceback
from bpy.props import (
    BoolProperty,
    EnumProperty,
    StringProperty,
)
from bpy.app.handlers import persistent
from .addon import prefs
from .property_utils import DynamicPG
from .debug_utils import *
from . import (
    pme,
    selection_state,
    operator_utils
)

MOUSE_BUTTONS = {
    'LEFTMOUSE', 'MIDDLEMOUSE', 'RIGHTMOUSE',
    'BUTTON4MOUSE', 'BUTTON5MOUSE', 'BUTTON6MOUSE', 'BUTTON7MOUSE'}
TWEAKS = {
    'EVT_TWEAK_L', 'EVT_TWEAK_M', 'EVT_TWEAK_R', 'EVT_TWEAK_A', 'EVT_TWEAK_S'}


key_items = []
key_names = {}
for i in bpy.types.Event.bl_rna.properties["type"].enum_items.values():
    key_items.append((i.identifier, i.name, "", i.value))
    key_names[i.identifier] = i.description or i.name

_keymap_names = {
    "Window": ('EMPTY', 'WINDOW'),
    "3D View": ('VIEW_3D', 'WINDOW'),
    "Timeline": ('TIMELINE', 'WINDOW'),
    "Graph Editor": ('GRAPH_EDITOR', 'WINDOW'),
    "Dopesheet": ('DOPESHEET_EDITOR', 'WINDOW'),
    "NLA Editor": ('NLA_EDITOR', 'WINDOW'),
    "Image": ('IMAGE_EDITOR', 'WINDOW'),
    "UV Editor": ('IMAGE_EDITOR', 'WINDOW'),
    "Sequencer": ('SEQUENCE_EDITOR', 'WINDOW'),
    "Clip Editor": ('CLIP_EDITOR', 'WINDOW'),
    "Text": ('TEXT_EDITOR', 'WINDOW'),
    "Node Editor": ('NODE_EDITOR', 'WINDOW'),
    "Logic Editor": ('LOGIC_EDITOR', 'WINDOW'),
    "Property Editor": ('PROPERTIES', 'WINDOW'),
    "Outliner": ('OUTLINER', 'WINDOW'),
    "User Preferences": ('USER_PREFERENCES', 'WINDOW'),
    "Info": ('INFO', 'WINDOW'),
    "File Browser": ('FILE_BROWSER', 'WINDOW'),
    "Console": ('CONSOLE', 'WINDOW'),
}

_keymaps_obj_mode = {
    "OBJECT": "Object Mode",
    "EDIT": "Mesh",
    "MESH": "Mesh",
    "POSE": "Pose",
    "SCULPT": "Sculpt",
    "VERTEX_PAINT": "Vertex Paint",
    "WEIGHT_PAINT": "Weight Paint",
    "TEXTURE_PAINT": "Image Paint",
    "CURVE": "Curve",
    "SURFACE": "Curve",
    "ARMATURE": "Armature",
    "META": "Metaball",
    "FONT": "Font",
    "LATTICE": "Lattice",
    "PARTICLE_EDIT": "Particle",
}


class _KMList:
    default_header = [
        "Screen Editing",
        "View2D",
        "Frames",
        "Header",
        "Window",
        "Screen"
    ]
    default_empty = [
        "Screen Editing",
        "Window",
        "Screen"
    ]

    def __init__(
            self, window=None, header=None, tools=None, ui=None,
            channels=None, preview=None):

        def init_rlist(lst):
            if lst is not None:
                lst.insert(0, "Screen Editing")
                lst.append("Window")
                lst.append("Screen")
            return lst

        self.rlists = {
            'WINDOW': init_rlist(window),
            'HEADER': init_rlist(header) if header else _KMList.default_header,
            'CHANNELS': init_rlist(channels),
            'TOOLS': init_rlist(tools),
            'TOOL_PROPS': tools,
            'UI': init_rlist(ui) if ui else tools,
            'PREVIEW': init_rlist(preview)
        }

    def get_keymaps(self, context):
        region = context.region.type
        if region in self.rlists and self.rlists[region]:
            return self.rlists[region]

        return _KMList.default_empty


class _View3DKMList(_KMList):
    def get_keymaps(self, context):
        region = context.region.type
        if region == 'WINDOW':
            lst = [
                "Screen Editing",
                "Grease Pencil"
            ]

            mode = "OBJECT"
            if context.active_object:
                mode = context.active_object.mode

            if mode == "EDIT":
                tp = context.active_object.type
                if tp in _keymaps_obj_mode:
                    lst.append(_keymaps_obj_mode[tp])
            else:
                lst.append(_keymaps_obj_mode[mode])

            lst.append("Object Non-modal")
            lst.append("Frames")
            lst.append("3D View Generic")
            lst.append("3D View")
            lst.append("Window")
            lst.append("Screen")

            return lst

        return super(_View3DKMList, self).get_keymaps(context)


class _ImageKMList(_KMList):
    def get_keymaps(self, context):
        region = context.region.type
        if region == 'WINDOW':
            lst = [
                "Screen Editing",
                "Frames",
                "Grease Pencil"
            ]

            mode = bpy.context.space_data.mode
            if mode == 'PAINT':
                lst.append("Image Paint")
            elif mode == 'MASK':
                lst.append("Mask Editing")
            elif mode == 'VIEW':
                ao = context.active_object
                if ao and ao.data and \
                        ao.type == 'MESH' and ao.mode == 'EDIT' and \
                        ao.data.uv_layers.active:
                    lst.append("UV Editor")

            lst.append("Image Generic")
            lst.append("Image")
            lst.append("Window")
            lst.append("Screen")

            return lst

        return super(_ImageKMList, self).get_keymaps(context)


_km_lists = {
    "VIEW_3D": _View3DKMList(
        header=[
            "View2D",
            "Frames",
            "Header",
            "3D View Generic"
        ],
        tools=[
            "Frames",
            "View2D Buttons List",
            "3D View Generic"
        ]),

    "TIMELINE": _KMList(
        window=[
            "View2D",
            "Markers",
            "Animation",
            "Frames",
            "Timeline"
        ]),

    "GRAPH_EDITOR": _KMList(
        window=[
            "View2D",
            "Animation",
            "Frames",
            "Graph Editor",
            "Graph Editor Generic"
        ],
        channels=[
            "View2D",
            "Frames",
            "Animation Channels",
            "Graph Editor Generic"
        ],
        tools=[
            "View2D Buttons List",
            "Graph Editor Generic"
        ]),

    "DOPESHEET_EDITOR": _KMList(
        window=[
            "View2D",
            "Animation",
            "Frames",
            "Dopesheet"
        ],
        channels=[
            "View2D",
            "Frames",
            "Animation Channels"
        ]),

    "NLA_EDITOR": _KMList(
        window=[
            "View2D",
            "Animation",
            "Frames",
            "NLA Editor",
            "NLA Generic"
        ],
        channels=[
            "View2D",
            "Frames",
            "NLA Channels",
            "Animation Channels",
            "NLA Generic"
        ],
        tools=[
            "View2D Buttons List",
            "NLA Generic"
        ]),

    "IMAGE_EDITOR": _ImageKMList(
        tools=[
            "Frames",
            "View2D Buttons List",
            "Image Generic"
        ]),

    "SEQUENCE_EDITOR": _KMList(
        window=[
            "View2D",
            "Animation",
            "Frames",
            "SequencerCommon",
            "Sequencer"
        ],
        preview=[
            "View2D",
            "Frames",
            "Grease Pencil",
            "SequencerCommon",
            "SequencerPreview"
        ],
        tools=[
            "Frames",
            "SequencerCommon",
            "View2D Buttons List"
        ]),

    "CLIP_EDITOR": _KMList(
        window=[
            "Frames",
            "Grease Pencil",
            "Clip",
            "Clip Editor"
        ],
        channels=[
            "Frames",
            "Clip Dopesheet Editor"
        ],
        preview=[
            "View2D",
            "Frames",
            "Clip",
            "Clip Graph Editor",
            "Clip Dopesheet Editor"
        ],
        tools=[
            "Frames",
            "View2D Buttons List",
            "Clip"
        ]),

    "TEXT_EDITOR": _KMList(
        window=[
            "Text Generic",
            "Text"
        ],
        header=[
            "View2D",
            "Header"
        ],
        tools=[
            "View2D Buttons List",
            "Text Generic"
        ]),

    "NODE_EDITOR": _KMList(
        window=[
            "View2D",
            "Frames",
            "Grease Pencil",
            "Node Generic",
            "Node Editor"
        ],
        header=[
            "View2D",
            "Header",
            "Frames"
        ],
        tools=[
            "Frames",
            "View2D Buttons List",
            "Node Generic"
        ]),

    "LOGIC_EDITOR": _KMList(
        window=[
            "View2D",
            "Frames",
            "Logic Editor"
        ],
        tools=[
            "Frames",
            "View2D Buttons List",
            "Logic Editor"
        ]),

    "PROPERTIES": _KMList(
        window=[
            "Frames",
            "View2D Buttons List",
            "Property Editor"
        ]),

    "OUTLINER": _KMList(
        window=[
            "View2D",
            "Frames",
            "Outliner"
        ]),

    "USER_PREFERENCES": _KMList(
        window=[
            "View2D Buttons List"
        ],
        header=[
            "View2D",
            "Header"
        ]),

    "INFO": _KMList(
        window=[
            "View2D",
            "Frames",
            "Info"
        ]),

    "FILE_BROWSER": _KMList(
        window=[
            "View2D",
            "File Browser",
            "File Browser Main"
        ],
        header=[
            "View2D",
            "Header",
            "File Browser"
        ],
        tools=[
            "View2D Buttons List",
            "File Browser"
        ],
        ui=[
            "File Browser",
            "File Browser Buttons"
        ]),

    "CONSOLE": _KMList(
        window=[
            "View2D",
            "Console"
        ],
        header=[
            "View2D",
            "Header"
        ])
}


def to_blender_mouse_key(key, context):
    default = context.user_preferences.inputs.select_mouse == 'RIGHT'

    if key == 'LEFTMOUSE':
        key = 'ACTIONMOUSE' if default else 'SELECTMOUSE'
    elif key == 'RIGHTMOUSE':
        key = 'SELECTMOUSE' if default else 'ACTIONMOUSE'

    return key


def to_system_mouse_key(key, context):
    default = context.user_preferences.inputs.select_mouse == 'RIGHT'

    if key == 'ACTIONMOUSE':
        key = 'LEFTMOUSE' if default else 'RIGHTMOUSE'
    elif key == 'SELECTMOUSE':
        key = 'RIGHTMOUSE' if default else 'LEFTMOUSE'

    return key


def compare_km_names(name1, name2):
    if name1 == name2:
        return 2

    name1 = set(s.strip() for s in name1.split(","))
    name2 = set(s.strip() for s in name2.split(","))
    name = name1.intersection(name2)

    if name == name1:
        return 2

    elif not name:
        return 0

    return 1


def parse_hotkey(hotkey):
    parts = hotkey.upper().split("+")

    ctrl = 'CTRL' in parts
    if ctrl:
        parts.remove('CTRL')

    alt = 'ALT' in parts
    if alt:
        parts.remove('ALT')

    shift = 'SHIFT' in parts
    if shift:
        parts.remove('SHIFT')

    oskey = 'OSKEY' in parts
    if oskey:
        parts.remove('OSKEY')

    key_mod = 'NONE' if len(parts) == 1 else parts[0]
    key = parts[-1]

    enum_items = bpy.types.Event.bl_rna.properties["type"].enum_items
    if key_mod not in enum_items:
        key_mod = 'NONE'
    if key not in enum_items:
        key = 'NONE'

    return key, ctrl, shift, alt, oskey, key_mod


def run_operator(context, key, ctrl, shift, alt, oskey, key_mod):
    area = context.area.type
    if area not in _km_lists:
        return

    key1 = key
    key2 = key
    default = context.user_preferences.inputs.select_mouse == 'RIGHT'

    if key == 'LEFTMOUSE':
        key2 = 'ACTIONMOUSE' if default else 'SELECTMOUSE'
    if key == 'RIGHTMOUSE':
        key2 = 'SELECTMOUSE' if default else 'ACTIONMOUSE'
    if key == 'ACTIONMOUSE':
        key2 = 'LEFTMOUSE' if default else 'RIGHTMOUSE'
    if key == 'SELECTMOUSE':
        key2 = 'RIGHTMOUSE' if default else 'LEFTMOUSE'

    km_names = _km_lists[area].get_keymaps(context)
    km_item = None
    keymaps = context.window_manager.keyconfigs.user.keymaps
    for km_name in km_names:
        if km_name not in keymaps:
            continue
        km = keymaps[km_name]
        for kmi in km.keymap_items:
            if (kmi.type == key1 or kmi.type == key2) and \
                    kmi.active and \
                    kmi.ctrl == ctrl and \
                    kmi.shift == shift and \
                    kmi.alt == alt and \
                    kmi.oskey == oskey and \
                    kmi.key_modifier == key_mod and \
                    kmi.idname != "pme.mouse_state" and \
                    kmi.idname != "wm.pme_user_pie_menu_call":
                module, _, operator = kmi.idname.rpartition(".")
                if not module or "." in module:
                    continue

                if not hasattr(bpy.ops, module):
                    continue
                module = getattr(bpy.ops, module)

                if not hasattr(module, operator):
                    continue
                operator = getattr(module, operator)
                if operator.poll():
                    km_item = kmi
                    break

        if km_item:
            break

    if not km_item:
        return

    module, operator = km_item.idname.split('.')
    module = getattr(bpy.ops, module)
    operator = getattr(module, operator)
    tp_name = operator.idname()
    tp = getattr(bpy.types, tp_name)
    props = tp.bl_rna.properties

    args = {}
    for k, i in km_item.properties.items():
        if "bpy id prop" in repr(i):
            continue

        args[k] = i
        if k in props:
            if hasattr(props[k], "enum_items"):
                enum_items = getattr(props[k], "enum_items")
                for item in enum_items:
                    if item.value == i:
                        args[k] = item.identifier
                        break

    try:
        operator('INVOKE_DEFAULT', True, **args)
    except:
        traceback.print_exc()


def run_operator_by_hotkey(context, hotkey):
    key, ctrl, shift, alt, oskey, key_mod = parse_hotkey(hotkey)

    run_operator(context, key, ctrl, shift, alt, oskey, key_mod)


def to_key_name(key):
    return key_names.get(key, key)


def to_hotkey(
        key, ctrl=False, shift=False, alt=False, oskey=False, key_mod=None,
        use_key_names=True):
    if not key or key == 'NONE':
        return ''

    hotkey = ''
    if ctrl:
        hotkey += 'ctrl+'
    if shift:
        hotkey += 'shift+'
    if alt:
        hotkey += 'alt+'
    if oskey:
        hotkey += 'oskey+'
    if key_mod and key_mod != 'NONE':
        hotkey += key_names[key_mod] if use_key_names else key_mod + "+"
    hotkey += key_names[key] if use_key_names else key
    return hotkey


class KeymapHelper:

    def __init__(self):
        self.keymap_items = {}
        self.km = None

    def _add_item(self, km, name, item):
        if km.name not in self.keymap_items:
            self.keymap_items[km.name] = []
        self.keymap_items[km.name].append(item)

    def available(self):
        return True if bpy.context.window_manager.keyconfigs.addon else False

    def keymap(self, name="Window", space_type='EMPTY', region_type='WINDOW'):
        keymaps = bpy.context.window_manager.keyconfigs.addon.keymaps
        bl_keymaps = bpy.context.window_manager.keyconfigs.default.keymaps

        if name not in keymaps:
            if name in bl_keymaps:
                space_type = bl_keymaps[name].space_type
                region_type = bl_keymaps[name].region_type
            elif name in _keymap_names:
                space_type = _keymap_names[name][0]
                region_type = _keymap_names[name][1]
            keymaps.new(
                name=name, space_type=space_type, region_type=region_type)

        self.km = keymaps[name]

    def menu(
            self, bl_class, hotkey=None,
            key='NONE', ctrl=False, shift=False, alt=False, oskey=False,
            key_mod='NONE'):
        if not self.km:
            return

        if hotkey:
            key, ctrl, shift, alt, oskey, key_mod = parse_hotkey(hotkey)

        item = self.km.keymap_items.new(
            'wm.call_menu', key, 'PRESS',
            ctrl=ctrl, shift=shift, alt=alt, oskey=oskey, key_modifier=key_mod)
        item.properties.name = bl_class.bl_idname

        self._add_item(self.km, hotkey, item)

        return item

    def operator(
            self, bl_class, hotkey=None,
            key='NONE', ctrl=False, shift=False, alt=False, oskey=False,
            key_mod='NONE', any=False):
        if not self.km:
            return

        if hotkey:
            key, ctrl, shift, alt, oskey, key_mod = parse_hotkey(hotkey)

        item = self.km.keymap_items.new(
            bl_class.bl_idname, key, 'PRESS',
            ctrl=ctrl, shift=shift, alt=alt, oskey=oskey, key_modifier=key_mod,
            any=any)

        if bl_class != PME_OT_key_state_init:
            n = len(self.km.keymap_items)
            i = n - 1
            ms_items = []
            keys = []
            while i >= 1 and self.km.keymap_items[i - 1].idname == \
                    PME_OT_key_state_init.bl_idname:
                ms_item = self.km.keymap_items[i - 1]
                ms_items.append(ms_item)
                keys.append(ms_item.type)
                i -= 1

            if ms_items:
                for ms_item in ms_items:
                    self.km.keymap_items.remove(ms_item)

                for key in keys:
                    self.km.keymap_items.new(
                        PME_OT_key_state_init.bl_idname,
                        key, 'PRESS', 1, 1, 1, 1, 1).properties.key = key

        self._add_item(self.km, hotkey, item)

        return item

    def pie(self, bl_class, hotkey=None,
            key='NONE', ctrl=False, shift=False, alt=False, oskey=False,
            key_mod='NONE'):
        if not self.km:
            return

        if hotkey:
            key, ctrl, shift, alt, oskey, key_mod = parse_hotkey(hotkey)

        item = self.km.keymap_items.new(
            'wm.call_menu_pie', key, 'PRESS',
            ctrl=ctrl, shift=shift, alt=alt, oskey=oskey, key_modifier=key_mod)
        item.properties.name = bl_class.bl_idname

        self._add_item(self.km, hotkey, item)

        return item

    def remove(self, item):
        if not self.km:
            return

        keymaps = bpy.context.window_manager.keyconfigs.addon.keymaps

        if self.km.name not in keymaps or \
                self.km.name not in self.keymap_items or \
                item not in self.keymap_items[self.km.name]:
            return

        try:
            keymaps[self.km.name].keymap_items.remove(item)
        except:
            pass

        self.keymap_items[self.km.name].remove(item)

    def unregister(self):
        keymaps = bpy.context.window_manager.keyconfigs.addon.keymaps

        for k, i in self.keymap_items.items():
            if k not in keymaps:
                continue

            for item in i:
                keymaps[k].keymap_items.remove(item)

        self.km = None
        self.keymap_items = None


def _hotkey_update(self, context):
    if self.hasvar("update"):
        pass

    if self.hasvar("kmis"):
        kmis = self.getvar("kmis")
        for kmi in kmis:
            self.to_kmi(kmi)


class Hotkey(DynamicPG):
    key = EnumProperty(
        items=key_items, description="Key pressed", update=_hotkey_update)
    ctrl = BoolProperty(
        description="Ctrl key pressed", update=_hotkey_update)
    shift = BoolProperty(
        description="Shift key pressed", update=_hotkey_update)
    alt = BoolProperty(
        description="Alt key pressed", update=_hotkey_update)
    oskey = BoolProperty(
        description="Operating system key pressed", update=_hotkey_update)
    key_mod = EnumProperty(
        items=key_items,
        description="Regular key pressed as a modifier",
        update=_hotkey_update)

    def add_kmi(self, kmi):
        if not self.hasvar("kmis"):
            self.setvar("kmis", [])
        self.getvar("kmis").append(kmi)
        return kmi

    def draw(self, layout):
        col = layout.column(True)
        col.prop(self, "key", "", event=True)
        row = col.row(True)
        row.prop(self, "ctrl", "Ctrl", toggle=True)
        row.prop(self, "shift", "Shift", toggle=True)
        row.prop(self, "alt", "Alt", toggle=True)
        row.prop(self, "oskey", "OSKey", toggle=True)
        row.prop(self, "key_mod", "", event=True)

    def from_kmi(self, kmi):
        self.key = kmi.type
        self.ctrl = kmi.ctrl
        self.shift = kmi.shift
        self.alt = kmi.alt
        self.oskey = kmi.oskey
        self.key_mod = kmi.key_modifier

    def to_kmi(self, kmi):
        kmi.type = self.key
        kmi.ctrl = self.ctrl
        kmi.shift = self.shift
        kmi.alt = self.alt
        kmi.oskey = self.oskey
        kmi.key_modifier = self.key_mod


class PME_OT_mouse_state(bpy.types.Operator):
    bl_idname = "pme.mouse_state"
    bl_label = ""
    bl_options = {'INTERNAL'}

    inst = None

    cancelled = BoolProperty(options={'SKIP_SAVE'})
    key = StringProperty(options={'SKIP_SAVE'})

    def stop(self):
        self.cancelled = True
        self.bl_timer = \
            bpy.context.window_manager.event_timer_add(0.1, bpy.context.window)

    def modal_stop(self, context):
        if self.bl_timer:
            context.window_manager.event_timer_remove(self.bl_timer)
            self.bl_timer = None

        if self.__class__.inst == self:
            self.__class__.inst = None

        return {'CANCELLED'}

    def modal(self, context, event):
        if event.type in TWEAKS:
            update_mouse_state(self.key)
            return {'PASS_THROUGH'}

        if event.type == 'WINDOW_DEACTIVATE':
            self.stop()
            return {'PASS_THROUGH'}

        if event.value == 'PRESS':
            if event.type == 'ESC':
                return {'CANCELLED'}
            elif event.type != 'MOUSEMOVE' and \
                    event.type != 'INBETWEEN_MOUSEMOVE':
                update_mouse_state(self.key)
                return {'PASS_THROUGH'}

        elif event.value == 'RELEASE':
            if event.type == self.key or event.type == 'WINDOW_DEACTIVATE':
                self.stop()

                if to_system_mouse_key(self.key, context) == 'RIGHTMOUSE':
                    self.key = 'NONE'
                    return {'RUNNING_MODAL'}

                self.key = 'NONE'

        elif event.type == 'TIMER':
            if self.cancelled:
                return self.modal_stop(context)

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        self.__class__.inst = self
        context.window_manager.modal_handler_add(self)

        return {'RUNNING_MODAL'}


class PME_OT_mouse_state_wait(bpy.types.Operator):
    bl_idname = "pme.mouse_state_wait"
    bl_label = ""
    bl_options = {'INTERNAL'}

    inst = None

    key = StringProperty(options={'SKIP_SAVE'})

    def stop(self):
        self.cancelled = True

    def modal(self, context, event):
        if event.type == 'ESC':
            self.__class__.inst = None
            return {'CANCELLED'}

        if event.type == 'TIMER':
            if self.cancelled:
                self.__class__.inst = None
                context.window_manager.event_timer_remove(self.bl_timer)
                self.bl_timer = None
                return {'CANCELLED'}

            bpy.ops.pme.mouse_state('INVOKE_DEFAULT', key=self.key)
            context.window_manager.event_timer_remove(self.bl_timer)
            self.bl_timer = None
            self.__class__.inst = None
            return {'CANCELLED'}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        self.cancelled = False
        context.window_manager.modal_handler_add(self)
        self.bl_timer = \
            context.window_manager.event_timer_add(0.0001, context.window)

        self.__class__.inst = self
        return {'RUNNING_MODAL'}


class PME_OT_mouse_state_init(bpy.types.Operator):
    bl_idname = "pme.mouse_state_init"
    bl_label = "Mouse State (PME)"
    bl_options = {'INTERNAL'}

    key = StringProperty(options={'SKIP_SAVE'})

    def invoke(self, context, event):
        if PME_OT_mouse_state.inst:
            if self.key != PME_OT_mouse_state.inst.key:
                return {'PASS_THROUGH'}
            PME_OT_mouse_state.inst.stop()
        if PME_OT_mouse_state_wait.inst:
            if self.key != PME_OT_mouse_state_wait.inst.key:
                return {'PASS_THROUGH'}
            PME_OT_mouse_state_wait.inst.stop()

        bpy.ops.pme.mouse_state_wait('INVOKE_DEFAULT', key=self.key)
        return {'PASS_THROUGH'}


class PME_OT_key_state(bpy.types.Operator):
    bl_idname = "pme.key_state"
    bl_label = ""
    bl_options = {'INTERNAL'}

    inst = None

    cancelled = BoolProperty(options={'SKIP_SAVE'})
    key = StringProperty(options={'SKIP_SAVE'})

    def stop(self):
        self.cancelled = True

    def modal_stop(self, context):
        if self.bl_timer:
            context.window_manager.event_timer_remove(self.bl_timer)
            self.bl_timer = None

        if self.__class__.inst == self:
            self.__class__.inst = None

        return {'CANCELLED'}

    def modal(self, context, event):
        # if event.type in TWEAKS:
        #     update_mouse_state(self.key)
        #     return {'PASS_THROUGH'}

        if event.type == 'WINDOW_DEACTIVATE':
            self.stop()
            return {'PASS_THROUGH'}

        if event.type == 'MOUSEMOVE' or \
                event.type == 'INBETWEEN_MOUSEMOVE':
            self.active = True
            return {'PASS_THROUGH'}

        # if event.value == 'PRESS':
        #     if event.type == 'ESC':
        #         return {'CANCELLED'}
        #     # elif event.type == 'MOUSEMOVE' or \
        #     #         event.type == 'INBETWEEN_MOUSEMOVE':
        #     #     self.active = True
        #     else:
        #         update_mouse_state(self.key)
        #         return {'PASS_THROUGH'}

        if event.value == 'RELEASE':
            if event.type == self.key:
                self.stop()

                # if to_system_mouse_key(self.key, context) == 'RIGHTMOUSE':
                #     self.key = 'NONE'
                #     return {'RUNNING_MODAL'}

                self.key = 'NONE'

        elif event.type == 'TIMER':
            if self.cancelled:
                return self.modal_stop(context)

            if not self.active:
                bpy.ops.pme.key_state('INVOKE_DEFAULT', key=self.key)
                return self.modal_stop(context)

            context.window.cursor_warp(event.mouse_x, event.mouse_y)
            self.active = False

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        self.active = True
        self.__class__.inst = self
        self.bl_timer = context.window_manager.event_timer_add(
            0.01, bpy.context.window)
        context.window_manager.modal_handler_add(self)

        return {'RUNNING_MODAL'}


class PME_OT_key_state_init(bpy.types.Operator):
    bl_idname = "pme.key_state_init"
    bl_label = "Key State Init(PME)"
    bl_options = {'INTERNAL'}

    key = StringProperty(options={'SKIP_SAVE'})

    def invoke(self, context, event):
        if PME_OT_key_state.inst:
            return {'PASS_THROUGH'}
        bpy.ops.pme.key_state('INVOKE_DEFAULT', key=self.key)
        return {'PASS_THROUGH'}


def is_key_pressed(key):
    ret = PME_OT_key_state.inst and PME_OT_key_state.inst.key == key
    return ret
    # return PME_OT_mouse_state.inst and PME_OT_mouse_state.inst.key == key or \
    #     PME_OT_mouse_state_wait.inst and \
    #     PME_OT_mouse_state_wait.inst.key == key


# def get_pressed_mouse_button():
#     if PME_OT_mouse_state.inst:
#         return PME_OT_mouse_state.inst.key
#     if PME_OT_mouse_state_wait.inst:
#         return PME_OT_mouse_state_wait.inst.key

#     return None


def update_mouse_state(key):
    pass
    # bpy.ops.pme.mouse_state_init('INVOKE_DEFAULT', key=key)


added_mouse_buttons = dict()


def add_mouse_button(key, kh, km="Screen Editing"):
    btn_key = key + km
    if btn_key not in added_mouse_buttons:
        added_mouse_buttons[btn_key] = 0

    added_mouse_buttons[btn_key] += 1

    if added_mouse_buttons[btn_key] == 1:
        kh.keymap(km)
        kh.operator(
            PME_OT_key_state_init,
            # PME_OT_mouse_state_init,
            None, key, 1, 1, 1, 1, any=True).properties.key = key


def remove_mouse_button(key, kh, km="Screen Editing"):
    btn_key = key + km
    if btn_key not in added_mouse_buttons:
        return

    added_mouse_buttons[btn_key] -= 1

    if added_mouse_buttons[btn_key] == 0:
        keymaps = bpy.context.window_manager.keyconfigs.addon.keymaps

        items = kh.keymap_items[km]
        for i, item in enumerate(items):
            if item.type == key and item.idname == "pme.mouse_state_init":
                keymaps[km].keymap_items.remove(item)
                items.pop(i)
                break


class PME_OT_key_is_pressed(bpy.types.Operator):
    bl_idname = "pme.key_is_pressed"
    bl_label = ""
    bl_options = {'INTERNAL'}

    inst = None
    instance = None
    idx = 1

    key = bpy.props.StringProperty(options={'SKIP_SAVE'})

    def add_timer(self, step=0):
        if self.timer:
            bpy.context.window_manager.event_timer_remove(self.timer)
        self.timer = bpy.context.window_manager.event_timer_add(
            step, bpy.context.window)

    def remove_timer(self):
        if self.timer:
            bpy.context.window_manager.event_timer_remove(self.timer)
            self.timer = None

    def stop(self):
        self.finished = True
        self.add_timer()

    def restart(self):
        self.restart_flag = True
        self.add_timer()

    def modal(self, context, event):
        if event.type == 'TIMER' and self.timer:
            if not self.is_pressed and self.timer.time_duration > 0.2:
                if self.instance:
                    self.instance.stop()
                self.stop()
                return {'PASS_THROUGH'}

            if self.finished:
                self.remove_timer()
                self.instance = None

                if PME_OT_key_is_pressed.inst == self:
                    PME_OT_key_is_pressed.inst = None
                return {'FINISHED'}

            elif self.restart_flag:
                self.remove_timer()
                ret = {'FINISHED'}
                if not self.instance:
                    ret = {'PASS_THROUGH'}
                    self.instance = self
                PME_OT_key_is_pressed.instance = self.instance
                bpy.ops.pme.key_is_pressed('INVOKE_DEFAULT', key=self.key)
                PME_OT_key_is_pressed.instance = None
                return ret

            return {'PASS_THROUGH'}

        if self.restart_flag:
            return {'PASS_THROUGH'}

        if event.type == 'WINDOW_DEACTIVATE':
            if self.instance:
                self.instance.stop()
            self.stop()

        elif event.type == 'MOUSEMOVE' or \
                event.type == 'INBETWEEN_MOUSEMOVE':
            return {'PASS_THROUGH'}

        if event.type == self.key:
            if event.value == 'RELEASE':
                if self.instance:
                    self.instance.stop()
                self.stop()

            elif event.value == 'PRESS':
                self.is_pressed = True
                if self.instance and self.timer:
                    self.remove_timer()

            return {'PASS_THROUGH'}

        if event.value != 'ANY' and event.value != 'NOTHING':
            self.restart()
            return {'PASS_THROUGH'}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        self.idx = self.__class__.idx
        self.__class__.idx += 1
        self.restart_flag = False
        self.instance = PME_OT_key_is_pressed.instance
        self.finished = False
        self.timer = None
        self.is_pressed = True
        if self.instance:
            self.is_pressed = False
            self.add_timer(0.02)
        if not PME_OT_key_is_pressed.inst:
            PME_OT_key_is_pressed.inst = self
        if not self.key:
            if event.value == 'RELEASE':
                return {'FINISHED'}
            self.key = event.type
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


def is_pressed(key):
    return PME_OT_key_is_pressed.inst and PME_OT_key_is_pressed.inst.key == key


def mark_pressed(event):
    if PME_OT_key_is_pressed.inst:
        return False

    bpy.ops.pme.key_is_pressed('INVOKE_DEFAULT', key=event.type)


class StackKey:
    name = None
    idx = -1
    is_first = True
    exec_locals = {}

    @staticmethod
    def next(pm):
        prop = pme.props.parse(pm.data)
        max_pmis = len(pm.pmis)
        StackKey.is_first = False
        if pm.name != StackKey.name or not selection_state.check():
            StackKey.idx = -1

        if StackKey.idx == -1:
            StackKey.is_first = True
            i = 0
            while i < max_pmis:
                if pm.pmis[i].mode != 'COMMAND':
                    break

                prop, value = operator_utils.find_statement(pm.pmis[i].text)
                if not prop:
                    break

                try:
                    if eval(prop) != eval(value):
                        break
                except:
                    break

                StackKey.idx = i
                i += 1

        StackKey.name = pm.name
        StackKey.idx += 1
        StackKey.idx %= max_pmis

        return pm.pmis[StackKey.idx]

    @staticmethod
    def reset():
        StackKey.name = None
        StackKey.is_first = True
        StackKey.idx = -1
        StackKey.exec_locals = pme.context.gen_locals()
