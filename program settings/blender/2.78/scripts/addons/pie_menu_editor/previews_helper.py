import bpy
import bpy.utils.previews
import os


class PreviewsHelper:

    def __init__(self, folder="icons"):
        self.path = os.path.join(os.path.dirname(__file__), folder)
        self.preview = None

    def get_icon(self, name):
        return self.preview[name].icon_id

    def get_icon_name_by_id(self, id):
        name = None
        min_id = 99999999
        for k, i in self.preview.items():
            if i.icon_id == id:
                return k
            if min_id > i.icon_id:
                min_id = i.icon_id
                name = k

        return name

    def get_names(self):
        return self.preview.keys()

    def has_icon(self, name):
        return name in self.preview

    def refresh(self):
        if self.preview:
            self.unregister()

        self.preview = bpy.utils.previews.new()
        for f in os.listdir(self.path):
            if not f.endswith(".png"):
                continue

            self.preview.load(
                os.path.splitext(f)[0],
                os.path.join(self.path, f),
                'IMAGE')

    def unregister(self):
        if not self.preview:
            return
        bpy.utils.previews.remove(self.preview)
        self.preview = None


if "ph" in globals():
    ph.unregister()

ph = PreviewsHelper()


def register():
    ph.refresh()


def unregister():
    ph.unregister()
