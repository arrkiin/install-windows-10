# Join 2 areas

# Usage 1 (Command tab):
# execute_script("scripts/command_area_join.py")

# Usage 2 (Command tab):
# from .scripts.command_area_join import join_area; join_area()

import bpy
from pie_menu_editor import pme


def join_area():
    a = bpy.context.area

    x, y, w, h = a.x, a.y, a.width, a.height
    r = (x + w + 2, y + h - 2, x + w - 2, y + h - 2)
    l = (x - 2, y + 2, x + 2, y + 2)
    t = (x + w - 2, y + h + 2, x + w - 2, y + h - 2)
    b = (x + 2, y - 2, x + 2, y + 2)

    mx, my = pme.context.event.mouse_x, pme.context.event.mouse_y
    cx, cy = x + 0.5 * w, y + 0.5 * h
    horizontal = (l, r) if mx < cx else (r, l)
    vertical = (b, t) if my < cy else (t, b)

    dx = min(mx - x, x + w - mx)
    dy = min(my - y, y + h - my)
    rects = vertical + horizontal if dy < dx else horizontal + vertical

    for rect in rects:
        if 'RUNNING_MODAL' in bpy.ops.screen.area_join(
                'INVOKE_DEFAULT', min_x=rect[0], min_y=rect[1],
                max_x=rect[2], max_y=rect[3]):
            break


join_area()
