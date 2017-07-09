import bpy
import blf
import bgl
from time import time
from .addon import ADDON_ID


class Timer:
    def __init__(self, t):
        self.reset(t)

    def update(self):
        t1 = time()
        self.t -= t1 - self.t0
        self.t0 = t1

        return self.t <= 0

    def reset(self, t):
        self.t = t
        self.t0 = time()

    def finished(self):
        return self.t <= 0


class SpaceGroup:
    def __init__(self, bl_type):
        self.type = bl_type
        self.handler = None
        self.bl_timer = None
        self.timer = Timer(1)
        self.text = None
        self.alignment = 'TOP'
        self.offset_x = 10
        self.offset_y = 10
        self.shadow = True


space_groups = dict(
    CLIP_EDITOR=SpaceGroup(bpy.types.SpaceClipEditor),
    CONSOLE=SpaceGroup(bpy.types.SpaceConsole),
    DOPESHEET_EDITOR=SpaceGroup(bpy.types.SpaceDopeSheetEditor),
    FILE_BROWSER=SpaceGroup(bpy.types.SpaceFileBrowser),
    GRAPH_EDITOR=SpaceGroup(bpy.types.SpaceGraphEditor),
    IMAGE_EDITOR=SpaceGroup(bpy.types.SpaceImageEditor),
    INFO=SpaceGroup(bpy.types.SpaceInfo),
    LOGIC_EDITOR=SpaceGroup(bpy.types.SpaceLogicEditor),
    NLA_EDITOR=SpaceGroup(bpy.types.SpaceNLA),
    NODE_EDITOR=SpaceGroup(bpy.types.SpaceNodeEditor),
    OUTLINER=SpaceGroup(bpy.types.SpaceOutliner),
    PROPERTIES=SpaceGroup(bpy.types.SpaceProperties),
    SEQUENCE_EDITOR=SpaceGroup(bpy.types.SpaceSequenceEditor),
    TEXT_EDITOR=SpaceGroup(bpy.types.SpaceTextEditor),
    TIMELINE=SpaceGroup(bpy.types.SpaceTimeline),
    USER_PREFERENCES=SpaceGroup(bpy.types.SpaceUserPreferences),
    VIEW_3D=SpaceGroup(bpy.types.SpaceView3D)
)


_line_y = 0


def _draw_line(space, r, g, b, a):
    ctx = bpy.context
    blf.size(0, space.size, 72)
    w, h = blf.dimensions(0, space.text)

    global _line_y

    if "LEFT" in space.alignment:
        x = space.offset_x
    elif "RIGHT" in space.alignment:
        x = ctx.region.width - w - space.offset_x
    else:
        x = 0.5 * ctx.region.width - 0.5 * w

    if "TOP" in space.alignment:
        _line_y += space.size + 3
        y = ctx.region.height - _line_y - space.offset_y
    else:
        y = _line_y + space.offset_y
        _line_y += space.size + 3

    blf.position(0, x, y, 0)
    bgl.glColor4f(r, g, b, a)
    blf.draw(0, space.text)


def _draw_text(space):
    r, g, b, a = space.color
    p = 1 if space.timer.t >= 0.3 else space.timer.t / 0.3

    if space.shadow:
        blf.enable(0, blf.SHADOW)
        blf.shadow_offset(0, 1, -1)
        blf.shadow(0, 5, 0.0, 0.0, 0.0, a * 0.4 * p)

    global _line_y
    _line_y = 0
    if space.text:
        _draw_line(space, r, g, b, a * p)

    blf.disable(0, blf.SHADOW)


class PME_OT_overlay(bpy.types.Operator):
    bl_idname = "pme.overlay"
    bl_label = ""
    bl_options = {'INTERNAL'}

    is_running = False

    text = bpy.props.StringProperty(options={'SKIP_SAVE'})

    def modal(self, context, event):
        if event.type == 'TIMER':
            num_handlers = 0
            active_areas = set()
            for name, space in space_groups.items():
                if not space.handler:
                    continue

                active_areas.add(name)

                if space.timer.update():
                    space.type.draw_handler_remove(
                        space.handler, 'WINDOW')
                    space.handler = None
                else:
                    num_handlers += 1

            for area in context.screen.areas:
                if area.type in active_areas:
                    area.tag_redraw()

            if not num_handlers:
                context.window_manager.event_timer_remove(self.timer)
                self.timer = None
                PME_OT_overlay.is_running = False
                return {'FINISHED'}

        return {'PASS_THROUGH'}

    def execute(self, context):
        if context.area.type not in space_groups:
            return {'CANCELLED'}

        pr = bpy.context.user_preferences.addons[ADDON_ID].preferences

        if not pr.overlay.overlay:
            return {'CANCELLED'}

        space = space_groups[context.area.type]
        space.timer.reset(pr.overlay.duration)
        space.text = self.text
        space.size = pr.overlay.size
        space.alignment = pr.overlay.alignment
        space.offset_x = pr.overlay.offset_x
        space.offset_y = pr.overlay.offset_y
        space.shadow = pr.overlay.shadow
        space.color = list(pr.overlay.color)

        if space.handler:
            return {'CANCELLED'}

        space.handler = space.type.draw_handler_add(
            _draw_text, (space,), 'WINDOW', 'POST_PIXEL')

        if not PME_OT_overlay.is_running:
            PME_OT_overlay.is_running = True
            context.window_manager.modal_handler_add(self)
            self.timer = context.window_manager.event_timer_add(
                0.1, bpy.context.window)

        return {'RUNNING_MODAL'}
