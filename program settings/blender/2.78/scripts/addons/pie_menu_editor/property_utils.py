import bpy
from types import BuiltinFunctionType
from mathutils import Euler

bpy.context.window_manager["pme_temp"] = dict()
IDPropertyGroup = type(bpy.context.window_manager["pme_temp"])
del bpy.context.window_manager["pme_temp"]

bpy.types.WindowManager.pme_temp = bpy.props.BoolVectorProperty(size=3)
BPyPropArray = type(bpy.context.window_manager.pme_temp)
del bpy.types.WindowManager.pme_temp


class _PGVars:
    uid = 0
    instances = {}

    @staticmethod
    def get(item):
        if not item.name:
            _PGVars.uid += 1
            item.name = str(_PGVars.uid)

        if item.name not in _PGVars.instances:
            _PGVars.instances[item.name] = _PGVars()

        return _PGVars.instances[item.name]


class DynamicPG(bpy.types.PropertyGroup):

    def getvar(self, var):
        pgvars = _PGVars.get(self)
        return getattr(pgvars, var)

    def hasvar(self, var):
        if not self.name or self.name not in _PGVars.instances:
            return False
        pgvars = _PGVars.get(self)
        return hasattr(pgvars, var)

    def setvar(self, var, value):
        pgvars = _PGVars.get(self)
        setattr(pgvars, var, value)
        return getattr(pgvars, var)


def to_dict(obj):
    dct = {}

    try:
        dct["name"] = obj["name"]
    except:
        pass

    for k in dir(obj.__class__):
        tup = getattr(obj.__class__, k)
        if not isinstance(tup, tuple) or len(tup) != 2 or \
                not isinstance(tup[0], BuiltinFunctionType):
            continue

        try:
            if tup[0] == bpy.props.CollectionProperty or \
                    tup[0] == bpy.props.PointerProperty:
                value = getattr(obj, k)
            else:
                value = obj[k]
        except:
            if "get" in tup[1]:
                continue

            value = getattr(obj, k)

        if tup[0] == bpy.props.PointerProperty:
            dct[k] = to_dict(value)

        elif tup[0] == bpy.props.CollectionProperty:
            dct[k] = []
            for item in value.values():
                dct[k].append(to_dict(item))

        elif isinstance(value, (bool, int, float, str)):
            dct[k] = value

    return dct


def from_dict(obj, dct):
    for k, value in dct.items():
        if isinstance(value, dict):
            from_dict(getattr(obj, k), value)

        elif isinstance(value, list):
            col = getattr(obj, k)
            col.clear()

            for item in value:
                from_dict(col.add(), item)

        else:
            obj[k] = value


def to_py_value(data, key, value):
    if isinstance(value, bpy.types.PropertyGroup):
        return None

    if isinstance(value, bpy.types.OperatorProperties):
        tp = getattr(bpy.types, key)
        if not tp:
            return None

        d = dict()
        for k in value.keys():
            py_value = to_py_value(tp, k, getattr(value, k))
            if py_value is None or isinstance(py_value, dict) and not py_value:
                continue
            d[k] = py_value

        return d

    is_bool = isinstance(data.bl_rna.properties[key], bpy.types.BoolProperty)

    if hasattr(value, "to_list"):
        value = value.to_list()
        if is_bool:
            value = [bool(v) for v in value]
    elif hasattr(value, "to_tuple"):
        value = value.to_tuple()
        if is_bool:
            value = tuple(bool(v) for v in value)
    elif isinstance(value, BPyPropArray):
        value = list(value)
        if is_bool:
            value = [bool(v) for v in value]
    elif isinstance(value, Euler):
        value = (value.x, value.y, value.z)

    return value


def is_enum(data, key):
    return isinstance(data.bl_rna.properties[key], bpy.types.EnumProperty)


def enum_id_to_value(data, key, id):
    for item in data.bl_rna.properties[key].enum_items:
        if item.identifier == id:
            return item.value
    return -1


def enum_value_to_id(data, key, value):
    return data.bl_rna.properties[key].enum_items[value].identifier
