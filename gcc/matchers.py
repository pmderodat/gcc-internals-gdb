import gdb

from gcc.tree import Tree


class MatchTree(gdb.Function):
    """
    Return whether a GCC tree matches expected tree code and name.

    For instance: matchtree(RECORD_TYPE, "foobar")
    """

    def __init__(self, name='matchtree'):
        super(MatchTree, self).__init__(name)

    def invoke(self, value, code, name):
        name = name.string() if name else None
        tree = Tree(value)
        return tree and tree.code == code and (not name or tree.name == name)
