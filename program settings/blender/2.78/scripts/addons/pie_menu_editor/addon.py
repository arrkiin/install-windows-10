import bpy
import os
import sys


ADDON_ID = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
ADDON_PATH = os.path.normpath(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_PATH = os.path.join(ADDON_PATH, "scripts/")
SAFE_MODE = "--pme-safe-mode" in sys.argv


def prefs():
    return bpy.context.user_preferences.addons[ADDON_ID].preferences


def temp_prefs():
    return bpy.context.window_manager.pme
