import gdb


class Tree(object):

    def __init__(self, value):
        self.value = value

    def __nonzero__(self):
        return bool(self.value)

    @property
    def code_class(self):
        return gdb.parse_and_eval(
            'tree_code_type[{}]'.format(int(self.code))
        )

    @property
    def struct(self):
        return self.value.dereference()

    @property
    def code(self):
        tree_code_type = gdb.lookup_type('enum tree_code')
        return self.value['base']['code'].cast(tree_code_type)

    @property
    def identifier_string(self):
        assert self.code == gdb.parse_and_eval('IDENTIFIER_NODE')
        ident = self.struct['identifier']['id']
        return ident['str']

    @property
    def name(self):
        # Declaration nodes are supposed to have either no name or an
        # IDENTIFIER_NODE.
        if self.code_class == gdb.parse_and_eval('tcc_declaration'):
            name = Tree(self.struct['decl_minimal']['name'])
            if not name:
                return None
            return name.identifier_string.string()

        # For their name, type nodes are allowed to have either no name, a
        # TYPE_DECL node or an IDENTIFIER_NODE.
        elif self.code_class == gdb.parse_and_eval('tcc_type'):
            name = Tree(self.struct['type_common']['name'])
            if not name:
                return None
            elif name.code == gdb.parse_and_eval('TYPE_DECL'):
                return name.name
            else:
                return name.identifier_string.string()

        else:
            raise ValueError('This node cannot have a name')
