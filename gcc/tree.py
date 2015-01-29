from functools import wraps

import gdb
import gdb.types


class Enum(object):
    def __init__(self, gdb_type):
        self.gdb_type = gdb_type
        self.name_to_value = gdb.types.make_enum_dict(gdb_type)
        self.value_to_name = {
            value: name
            for name, value in self.name_to_value.items()
        }

    def __getattr__(self, name):
        return gdb.Value(self.name_to_value[name]).cast(self.gdb_type)


tree_code_class = Enum(gdb.lookup_type('enum tree_code_class'))
tree_code = Enum(gdb.lookup_type('enum tree_code'))


def check_code_for_primitive(primitive, tree, tree_codes, tree_code_classes):
    if (
        tree.code not in tree_codes
        and tree.code_class not in tree_code_classes
    ):
        raise ValueError('Invalid "{}" primitive for {}'.format(
            primitive.__name__,
            tree.code
        ))


def primitive(*codes):
    tree_codes = [c for c in codes if c.type == tree_code.gdb_type]
    tree_code_classes = [
        c for c in codes if c.type == tree_code_class.gdb_type
    ]
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            check_code_for_primitive(func, self, tree_codes, tree_code_classes)
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


class Tree(object):
    """Python wrapper around `tree` values to ease data access."""

    def __init__(self, value):
        """
        Build a wrapper around a `tree` value.

        `value` can be either a gdb.Value instance, a string (in which case it
        is converted into a gdb.Value thanks to gdb.parse_and_eval) or an
        integer (in which case it is casted into a tree).
        """
        if isinstance(value, basestring):
            value = gdb.parse_and_eval(value)
        elif isinstance(value, int):
            value = gdb.Value(value).cast(gdb.lookup_type('tree'))
        self.value = value

    #
    # Common tree primitives
    #

    def __nonzero__(self):
        return bool(self.value)

    @property
    def struct(self):
        return self.value.dereference()

    @property
    def address(self):
        return int(self.value.cast(gdb.lookup_type('unsigned long long')))

    @property
    def code_class(self):
        return gdb.parse_and_eval(
            'tree_code_type[{}]'.format(int(self.code))
        )

    @property
    def code(self):
        return self.struct['base']['code'].cast(tree_code.gdb_type)

    def get_operand(self, i):
        return Tree(self.struct['exp']['operands'][i])

    #
    # Specialized primitives
    #

    @property
    @primitive(tree_code.IDENTIFIER_NODE)
    def identifier_string(self):
        return self.struct['identifier']['id']['str'].string()

    @property
    def name(self):
        # Declaration nodes are supposed to have either no name or an
        # IDENTIFIER_NODE.
        if self.code_class == tree_code_class.tcc_declaration:
            if not self.decl_name:
                return None
            return self.decl_name.identifier_string

        # For their name, type nodes are allowed to have either no name, a
        # TYPE_DECL node or an IDENTIFIER_NODE.
        elif self.code_class == gdb.parse_and_eval('tcc_type'):
            if not self.type_name:
                return None
            elif self.type_name.code == tree_code.TYPE_DECL:
                return self.type_name.decl_name.identifier_string
            else:
                return self.type_name.identifier_string

        else:
            raise ValueError('{} have no name'.format(self.code))

    @property
    @primitive(tree_code_class.tcc_declaration)
    def chain(self):
        return Tree(self.struct['common']['chain'])

    def __repr__(self):
        if not self.value:
            return 'NULL_TREE'
        try:
            name = self.name
        except ValueError:
            name = None
        return '<{} {}{}>'.format(
            str(self.code).lower(),
            hex(self.address),
            ' ' + name if name else ''
        )

    # BIND_EXPR

    @property
    @primitive(tree_code.BIND_EXPR)
    def bind_vars(self):
        return self.chain_to_list(self.get_operand(0), lambda x: x.chain)

    @property
    @primitive(tree_code.BIND_EXPR)
    def bind_body(self):
        return self.get_operand(1)

    @property
    @primitive(tree_code.BIND_EXPR)
    def bind_block(self):
        return self.get_operand(2)

    # BLOCK

    @property
    @primitive(tree_code.BLOCK)
    def block_vars(self):
        return self.chain_to_list(
            Tree(self.struct['block']['vars']),
            lambda x: x.chain
        )

    @property
    @primitive(tree_code.BLOCK)
    def block_subblocks(self):
        return self.chain_to_list(
            Tree(self.struct['block']['subblocks']),
            lambda x: x.block_chain
        )

    @property
    @primitive(tree_code.BLOCK)
    def block_superblock(self):
        return Tree(self.struct['block']['supercontext'])

    @property
    @primitive(tree_code.BLOCK)
    def block_chain(self):
        return Tree(self.struct['block']['chain'])

    # TYPE'S

    @property
    @primitive(tree_code_class.tcc_type)
    def type_variants(self):
        return self.chain_to_list(
            Tree(self.struct['type_common']['main_variant']),
            lambda x: Tree(self.struct['type_common']['next_variant'])
        )

    @property
    @primitive(tree_code_class.tcc_type)
    def type_name(self):
        return Tree(self.struct['type_common']['name'])

    # DECL'S

    @property
    @primitive(tree_code_class.tcc_declaration)
    def decl_name(self):
        return Tree(self.struct['decl_minimal']['name'])

    # Various helpers

    def chain_to_list(self, start, next_func):
        """
        Turn a chain of tree nodes into a list.

        Fetch the chain tarting at `start` and following links calling
        next_func (`next = next_func(start)`).
        """
        result = []
        while start:
            result.append(start)
            start = next_func(start)
        return result


class TreePrinter(object):
    name = 'tree'

    def __init__(self, value):
        self.value = value

    def to_string(self):
        return str(Tree(self.value))
