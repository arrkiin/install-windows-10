# Draw the message

# Usage 1 (Custom tab):
# execute_script("scripts/custom_hello_world.py", msg="My Message")

# Usage 2 (Custom tab):
# from .scripts.custom_hello_world import say_hello; say_hello("My Message")

from pie_menu_editor import pme


def say_hello(msg, icon='NONE', icon_value=0):
    box = pme.context.layout.box()
    box.label(msg, icon=icon, icon_value=icon_value)


msg = locals().get("kwargs", {}).get("msg", pme.context.text or "Hello World!")
say_hello(msg, pme.context.icon, pme.context.icon_value)
