# Open context sensitive menu

# Usage 1 (Command tab):
# execute_script("scripts/command_context_sensitive_menu.py")

# Usage 2 (Command tab):
# from .scripts.command_context_sensitive_menu import open_csm; open_csm()

import bpy
from pie_menu_editor import pme


def open_csm():
    context = bpy.context
    obj = context.selected_objects and context.active_object
    open_menu = pme.context.open_menu

    if not obj:
        open_menu("None Object")

    elif obj.type == "MESH":
        if obj.mode == 'EDIT':
            msm = context.tool_settings.mesh_select_mode
            msm[0] and open_menu("Vertex") or \
                msm[1] and open_menu("Edge") or \
                msm[2] and open_menu("Face") or \
                open_menu("Edit") or \
                open_menu("Mesh") or \
                open_menu("Any Object")

        else:
            open_menu(obj.mode.replace("_", " ").title()) or \
                open_menu("Mesh") or \
                open_menu("Any Object")

    else:
        open_menu(obj.mode.replace("_", " ").title()) or \
            open_menu(obj.type.replace("_", " ").title()) or \
            open_menu("Any Object")


open_csm()
