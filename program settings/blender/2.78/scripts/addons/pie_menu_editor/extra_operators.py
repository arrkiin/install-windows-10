import bpy


class PME_OT_dummy(bpy.types.Operator):
    bl_idname = "pme.dummy"
    bl_label = ""
    bl_options = {'INTERNAL', 'REGISTER', 'UNDO'}

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        return {'FINISHED'}


class PME_OT_none(bpy.types.Operator):
    bl_idname = "pme.none"
    bl_label = ""
    bl_options = {'INTERNAL'}

    pass_through = bpy.props.BoolProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        return {'PASS_THROUGH' if self.pass_through else 'CANCELLED'}

    def invoke(self, context, event):
        return {'PASS_THROUGH' if self.pass_through else 'CANCELLED'}


class WM_OT_pme_sidebar_toggle(bpy.types.Operator):
    bl_idname = "wm.pme_sidebar_toggle"
    bl_label = ""
    bl_description = ""
    bl_options = {'INTERNAL'}
    ops = dict(
        VIEW_3D=("view3d", "toolshelf", "properties"),
        GRAPH_EDITOR=("graph", None, "properties"),
        NLA_EDITOR=("nla", None, "properties"),
        IMAGE_EDITOR=("image", "toolshelf", "properties"),
        SEQUENCE_EDITOR=("sequencer", None, "properties"),
        CLIP_EDITOR=("clip", "tools", "properties"),
        TEXT_EDITOR=("text", None, "properties"),
        NODE_EDITOR=("node", "toolbar", "properties"),
        LOGIC_EDITOR=("logic", None, "properties"),
    )

    tools = bpy.props.BoolProperty()

    def execute(self, context):
        area = context.area
        if area.type in WM_OT_pme_sidebar_toggle.ops:
            op = WM_OT_pme_sidebar_toggle.ops[area.type]
            mod_name, tools_name, props_name = op

            name = tools_name if self.tools and tools_name else props_name
            mod = getattr(bpy.ops, mod_name)
            getattr(mod, name)()

        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return context.area.type in WM_OT_pme_sidebar_toggle.ops


class PME_OT_modal_dummy(bpy.types.Operator):
    bl_idname = "pme.modal_dummy"
    bl_label = "Dummy Modal"

    message = bpy.props.StringProperty(
        name="Message", options={'SKIP_SAVE'},
        default="OK: Enter/LClick, Cancel: Esc/RClick)")

    def modal(self, context, event):
        if event.value == 'PRESS':
            if event.type in {'ESC', 'RIGHTMOUSE'}:
                context.area.header_text_set()
                return {'CANCELLED'}
            elif event.type in {'RET', 'LEFTMOUSE'}:
                context.area.header_text_set()
                return {'FINISHED'}
        return {'RUNNING_MODAL'}

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        context.area.header_text_set(self.message)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


class PME_OT_screen_set(bpy.types.Operator):
    bl_idname = "pme.screen_set"
    bl_label = "Set Screen By Name"

    name = bpy.props.StringProperty()

    def execute(self, context):
        if self.name not in bpy.data.screens:
            return {'CANCELLED'}

        if context.screen.show_fullscreen:
            bpy.ops.screen.back_to_previous()

        if context.screen.show_fullscreen:
            bpy.ops.screen.back_to_previous()

        context.window.screen = bpy.data.screens[self.name]

        return {'FINISHED'}


# class PME_OT_macro_spacer(bpy.types.Operator):
#     bl_idname = "pme.macro_spacer"
#     bl_label = "Macro Spacer (PME)"

#     instance = None

#     key = bpy.props.StringProperty(options={'SKIP_SAVE'})

#     def add_timer(self, step=0):
#         if self.timer:
#             bpy.context.window_manager.event_timer_remove(self.timer)
#         self.timer = bpy.context.window_manager.event_timer_add(
#             step, bpy.context.window)

#     def remove_timer(self):
#         if self.timer:
#             bpy.context.window_manager.event_timer_remove(self.timer)
#             self.timer = None

#     def stop(self):
#         self.finished = True
#         self.add_timer()

#     def restart(self):
#         self.restart_flag = True
#         self.add_timer()

#     def modal(self, context, event):
#         if event.type == 'TIMER' and self.timer:
#             if not self.is_pressed and self.timer.time_duration > 0.2:
#                 if self.instance:
#                     self.instance.stop()
#                 self.stop()
#                 return {'PASS_THROUGH'}

#             if self.finished:
#                 self.remove_timer()
#                 self.instance = None
#                 return {'FINISHED'}

#             elif self.restart_flag:
#                 self.remove_timer()
#                 ret = {'FINISHED'}
#                 if not self.instance:
#                     ret = {'PASS_THROUGH'}
#                     self.instance = self
#                 PME_OT_macro_spacer.instance = self.instance
#                 bpy.ops.pme.macro_spacer('INVOKE_DEFAULT', key=self.key)
#                 PME_OT_macro_spacer.instance = None
#                 return ret

#             return {'PASS_THROUGH'}

#         if self.restart_flag:
#             return {'PASS_THROUGH'}

#         if event.type == 'WINDOW_DEACTIVATE':
#             self.stop()

#         elif event.type == 'MOUSEMOVE' or \
#                 event.type == 'INBETWEEN_MOUSEMOVE':
#             return {'PASS_THROUGH'}

#         if event.type == self.key:
#             if event.value == 'RELEASE':
#                 if self.instance:
#                     self.instance.stop()
#                 self.stop()

#             elif event.value == 'PRESS':
#                 self.is_pressed = True
#                 if self.instance and self.timer:
#                     self.remove_timer()

#             return {'PASS_THROUGH'}

#         if event.value != 'ANY' and event.value != 'NOTHING':
#             self.restart()
#             return {'PASS_THROUGH'}

#         return {'PASS_THROUGH'}

#     def invoke(self, context, event):
#         self.restart_flag = False
#         self.instance = PME_OT_macro_spacer.instance
#         self.finished = False
#         self.timer = None
#         self.is_pressed = True
#         if self.instance:
#             self.is_pressed = False
#             self.add_timer(0.02)
#         if not self.key:
#             if event.value == 'RELEASE':
#                 return {'FINISHED'}
#             self.key = event.type
#         context.window_manager.modal_handler_add(self)
#         return {'RUNNING_MODAL'}