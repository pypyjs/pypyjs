from _ctypes import structure

class UnionMeta(structure.StructOrUnionMeta):
    _is_union = True

class Union(structure.StructOrUnion):
    __metaclass__ = UnionMeta
