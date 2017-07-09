import bpy
import bmesh
from .debug_utils import *


def _get_mode():
    C = bpy.context

    def VIEW_3D():
        return "%s:%s" % (C.area.type, C.mode)

    def PROPERTIES():
        return "%s:%s" % (C.area.type, C.space_data.context)

    atype = C.area.type
    if atype and atype in locals():
        return locals()[atype]()

    if C.space_data and hasattr(C.space_data, "mode"):
        return "%s:%s" % (atype, C.space_data.mode)

    return atype


def _get_data():
    C = bpy.context

    def VIEW_3D():
        def _EDIT():
            def MESH():
                ret = []
                bm = bmesh.from_edit_mesh(C.active_object.data)
                sm = C.tool_settings.mesh_select_mode
                if sm[0]:
                    bm.verts.ensure_lookup_table()
                    bm.verts.index_update()
                    elems = [e.index for e in bm.verts if e.select]
                    ret.append('VERTEX')
                    ret.extend(elems)
                if sm[1]:
                    bm.edges.ensure_lookup_table()
                    bm.edges.index_update()
                    elems = [e.index for e in bm.edges if e.select]
                    ret.append('EDGE')
                    ret.extend(elems)
                if sm[2]:
                    bm.faces.ensure_lookup_table()
                    bm.faces.index_update()
                    elems = [e.index for e in bm.faces if e.select]
                    ret.append('FACE')
                    ret.extend(elems)

                return ret

            def CURVE():
                ret = []
                data = C.object.data
                for i, s in enumerate(data.splines):
                    ret.append(i)
                    if s.type == 'BEZIER':
                        for j, p in enumerate(s.bezier_points):
                            if p.select_control_point:
                                ret.append(j)
                    else:
                        for j, p in enumerate(s.points):
                            if p.select:
                                ret.append(j)

                return ret

            def META():
                ret = []

                elems = C.object.data.elements
                for i, e in enumerate(elems):
                    if e == elems.active:
                        ret.append(i)
                        break

                return ret

            def SURFACE():
                return CURVE()

            def ARMATURE():
                ret = []
                for i, b in enumerate(C.object.data.edit_bones):
                    if b.select:
                        ret.append(i)
                        break
                return ret

            def LATTICE():
                ret = []
                for i, p in enumerate(C.object.data.points):
                    if p.select:
                        ret.append(i)
                        break
                return ret

            if not C.active_object:
                return None

            otype = C.active_object.type
            if otype in locals():
                return locals()[otype]()

            return None

        def _OBJECT():
            ret = [obj.name for obj in C.selected_objects]
            ret.append(C.active_object.name if C.active_object else "None")
            return ret

        def OBJECT():
            return _OBJECT()

        def SCULPT():
            return _OBJECT()

        def EDIT():
            return _EDIT()

        def TEXTURE_PAINT():
            if not C.active_object or not C.active_object.data.use_paint_mask:
                return None
            bpy.ops.object.mode_set(mode='EDIT')
            ret = _EDIT()
            bpy.ops.object.mode_set(mode='TEXTURE_PAINT')
            return ret

        def VERTEX_PAINT():
            if not C.active_object or not C.active_object.data.use_paint_mask:
                return None
            bpy.ops.object.mode_set(mode='EDIT')
            ret = _EDIT()
            bpy.ops.object.mode_set(mode='VERTEX_PAINT')
            return ret

        def WEIGHT_PAINT():
            if not C.active_object or not C.active_object.data.use_paint_mask:
                return None
            bpy.ops.object.mode_set(mode='EDIT')
            ret = _EDIT()
            bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
            return ret

        def POSE():
            ret = []
            for i, b in enumerate(C.object.pose.bones):
                if b.bone.select:
                    ret.append(i)
                    break
            return ret

        def GPENCIL_EDIT():
            ret = []
            for i, s in enumerate(C.editable_gpencil_strokes):
                ret.append(i)
                for j, p in enumerate(s.points):
                    if p.select:
                        ret.append(j)
            return ret

        if C.object and C.object.mode in locals():
            return locals()[C.object.mode]()

        return None

    def IMAGE_EDITOR():
        ao = C.active_object
        if ao and ao.type == 'MESH' and ao.mode == 'EDIT':
            bm = bmesh.from_edit_mesh(ao.data)
            uvl = bm.loops.layers.uv.active
            if uvl:
                ret = set()
                for f in bm.faces:
                    for l in f.loops:
                        if l[uvl].select:
                            ret.add(l.index)

                return ret

        return None

    def TIMELINE():
        return [m.name for m in C.scene.timeline_markers if m.select]

    def NODE_EDITOR():
        if not hasattr(C, "selected_nodes"):
            return None
        return [n.name for n in C.selected_nodes]

    def SEQUENCE_EDITOR():
        return [seq.name for seq in C.selected_sequences]

    atype = C.area.type
    if atype and atype in locals():
        return locals()[atype]()

    return None


def _get_ao():
    if bpy.context.active_operator:
        return bpy.context.active_operator.bl_idname
    return None


class SelectionState:
    def __init__(self):
        self.ao = None
        self.mode = None
        self.data = None

    def update(self):
        self.ao = _get_ao()
        self.mode = _get_mode()
        self.data = _get_data()

    def __str__(self):
        return "[%s] %s" % (self.mode, self.data)


_state = SelectionState()


def check():
    ao = _get_ao()
    if not _state.ao or _state.ao != ao:
        return False

    mode = _get_mode()
    if _state.mode != mode:
        return False

    data = _get_data()
    if _state.data != data:
        return False

    return True


def update():
    DBG and logh("Update SelectionState")
    _state.update()

