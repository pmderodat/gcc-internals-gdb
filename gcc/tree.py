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
tree_node_structure_enum = Enum(
    gdb.lookup_type('enum tree_node_structure_enum')
)
tree_contains_struct = gdb.parse_and_eval('tree_contains_struct')


def check_code_for_primitive(
    primitive, tree,
    tree_node_structures, tree_codes, tree_code_classes
):
    if (
        tree.code not in tree_codes
        and tree.code_class not in tree_code_classes
        and not any(
            tree_contains_struct[tree.code][tree_node_structure]
            for tree_node_structure in tree_node_structures
        )
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
    tree_node_structures = [
        c for c in codes if c.type == tree_node_structure_enum.gdb_type
    ]
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if not self.value:
                raise ValueError('Trying to inspect NULL_TREE')
            check_code_for_primitive(
                func, self,
                tree_node_structures, tree_codes, tree_code_classes
            )
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

    def get_tree_field(self, union_field, struct_field):
        return Tree(self.struct[union_field][struct_field])

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
    @primitive(tree_code_class.tcc_type, tree_code_class.tcc_declaration)
    def context(self):
        if self.code_class == tree_code_class.tcc_type:
            return self.get_tree_field('type_common', 'context')
        elif self.code_class == tree_code_class.tcc_declaration:
            return self.get_tree_field('decl_minimal', 'context')
        else:
            raise ValueError('{} have no context'.format(self.code))

    # TODO: check the "typed?" predicate just like GCC does.
    @property
    @primitive(tree_node_structure_enum.TS_TYPED)
    def type(self):
        return self.get_tree_field('typed', 'type')

    @property
    @primitive(tree_code_class.tcc_declaration)
    def chain(self):
        return self.get_tree_field('common', 'chain')

    @property
    @primitive(tree_code_class.tcc_declaration)
    def decl_to_chain_list(self):
        return self.chain_to_list(self, lambda x: x.chain)

    @property
    @primitive(tree_code.TREE_LIST)
    def list_chain(self):
        return self.get_tree_field('common', 'chain')

    @property
    @primitive(tree_code.TREE_LIST)
    def list_value(self):
        return self.get_tree_field('list', 'value')

    def __repr__(self):
        if not self.value:
            return 'NULL_TREE'

        def get_suffix():
            if self.code == tree_code.IDENTIFIER_NODE:
                return self.identifier_string

            try: return str(self.int_cst)
            except: pass

            try: return self.name
            except ValueError: pass

        suffix = get_suffix()
        return '<{} {}{}>'.format(
            str(self.code).lower(),
            hex(self.address),
            ' ' + suffix if suffix else ''
        )

    # INTEGER_CST

    @property
    @primitive(tree_code.INTEGER_CST)
    def int_cst(self):
        double_struct = self.struct['int_cst']['int_cst']
        low = double_struct['low']
        high = double_struct['high']
        return int(high) << (8 * low.type.sizeof) | int(low)

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
    def block_is_abstract(self):
        return bool(self.struct['block']['abstract_flag'])

    @property
    @primitive(tree_code.BLOCK)
    def block_abstract_origin(self):
        return self.get_tree_field('block', 'abstract_origin')

    @property
    @primitive(tree_code.BLOCK)
    def block_vars(self):
        return self.chain_to_list(
            self.get_tree_field('block', 'vars'),
            lambda x: x.chain
        )

    @property
    @primitive(tree_code.BLOCK)
    def block_subblocks(self):
        return self.chain_to_list(
            self.get_tree_field('block', 'subblocks'),
            lambda x: x.block_chain
        )

    @property
    @primitive(tree_code.BLOCK)
    def block_superblock(self):
        return self.get_tree_field('block', 'supercontext')

    @property
    @primitive(tree_code.BLOCK)
    def block_chain(self):
        return self.get_tree_field('block', 'chain')

    # TYPE'S

    @property
    @primitive(tree_code_class.tcc_type)
    def type_variants(self):
        return self.chain_to_list(
            self.get_tree_field('type_common' ,'main_variant'),
            lambda x: self.get_tree_field('type_common', 'next_variant')
        )

    @property
    @primitive(tree_code_class.tcc_type)
    def type_name(self):
        return self.get_tree_field('type_common', 'name')

    @property
    @primitive(tree_code_class.tcc_type)
    def type_size(self):
        return self.get_tree_field('type_common', 'size')

    @property
    @primitive(tree_code_class.tcc_type)
    def type_size_unit(self):
        return self.get_tree_field('type_common', 'size_unit')

    @property
    @primitive(tree_code_class.tcc_type)
    def type_stub_decl(self):
        return self.get_tree_field('common', 'chain')

    def _get_values_chain(self):
        return self.chain_to_list(
            self.get_tree_field('type_non_common', 'values'),
            lambda x: x.list_chain,
            lambda x: x.list_value
        )

    @property
    @primitive(tree_code.RECORD_TYPE, tree_code.UNION_TYPE)
    def type_fields(self):
        return self.chain_to_list(
            self.get_tree_field('type_non_common', 'values'),
            lambda x: x.chain
        )

    @property
    @primitive(tree_code.FUNCTION_TYPE, tree_code.METHOD_TYPE)
    def arg_types(self):
        return self._get_values_chain()

    @property
    @primitive(tree_code.RECORD_TYPE,
               tree_code.UNION_TYPE,
               tree_code.QUAL_UNION_TYPE)
    def type_methods(self):
        return self.chain_to_list(
            self.get_tree_field('type_non_common', 'maxval'),
            lambda x: x.chain
        )

    # DECL'S

    @property
    @primitive(tree_code_class.tcc_declaration)
    def decl_name(self):
        return self.get_tree_field('decl_minimal', 'name')

    @property
    @primitive(tree_code.TYPE_DECL)
    def decl_original_type(self):
        return self.get_tree_field('decl_non_common', 'result')

    # FUNCTION_DECL

    @property
    @primitive(tree_code.FUNCTION_DECL)
    def saved_tree(self):
        return self.get_tree_field('decl_non_common', 'saved_tree')

    # STATEMENT_LIST

    @property
    @primitive(tree_code.STATEMENT_LIST)
    def statements(self):
        return self.chain_to_list(
            self.struct['stmt_list']['head'],
            lambda x: x['next'],
            lambda x: Tree(x['stmt'])
        )

    # Various helpers

    def chain_to_list(self, start, next_func, get_elt_func=None):
        """
        Turn a chain of tree nodes into a list.

        Fetch the chain tarting at `start` and following links calling
        next_func (`next = next_func(start)`). If `get_elt_func` is provided,
        return elements are mapped with it.
        """
        result = []
        while start:
            result.append(get_elt_func(start) if get_elt_func else start)
            start = next_func(start)
        return result


class TreePrinter(object):
    name = 'tree'

    def __init__(self, value):
        self.value = value

    def to_string(self):
        return str(Tree(self.value))
