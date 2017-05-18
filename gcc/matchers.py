import gdb

from gcc.tree import Tree, tree_code


class MatchTree(gdb.Function):
    """
    Return whether a GCC tree matches expected tree code and name.

    For instance: matchtree(node, RECORD_TYPE, "foobar")
    """

    def __init__(self, name='matchtree'):
        super(MatchTree, self).__init__(name)

    def invoke(self, value, code, name):
        name = name.string() if name else None
        tree = Tree(value)
        if not tree or code != code:
            return False

        if not name:
            return True

        if tree.code == tree_code.IDENTIFIER_NODE:
            tree_name = tree.identifier_string
        else:
            try:
                tree_name = tree.name
            except ValueError:
                tree_name = None
        return tree_name == name
