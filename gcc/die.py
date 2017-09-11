import gdb
import gdb.types

from gcc.utils import Enum, is_string, ptr_to_int


dwarf_attribute = Enum(gdb.lookup_type('enum dwarf_attribute'))
dw_val_class = Enum(gdb.lookup_type('enum dw_val_class'))


class DIE(object):
    """
    Python wrapper around `dw_die_ref` values to ease data access.
    """


    def __init__(self, value):
        if is_string(value):
            value = gdb.parse_and_eval(value)
        elif isinstance(value, int):
            value = gdb.Value(value).caste(gdb.lookup_type('dw_die_ref'))

        self.value = value

    def __nonzero__(self):
        return bool(self.value)

    def __eq__(self, other):
        return other and self.value == other.value

    def __hash__(self):
        return hash(self.address)

    def __getitem__(self, key):
        """
        If `key` is an integer, use it as an index to get the KEY'th attribute.
        Raise an IndexError if this index is out of bounds.

        If it's a string, consider it's an enum dwarf_attribute value and look
        for the corresponding attribute to return it. Raise a ValueError if
        there is no such enum dwarf_attribute value and raise a KeyError if
        there is no such attribute.
        """
        if isinstance(key, int):
            return self.attributes[key]

        assert isinstance(key, basestring)
        attr = dwarf_attribute.name_to_value[key]
        for c in self.attributes:
            if c.attr == attr:
                return c
        raise KeyError('No such attribute: {}'.format(attr))

    @property
    def struct(self):
        return self.value.dereference()

    @property
    def address(self):
        return ptr_to_int(self.value)

    @property
    def tag(self):
        return self.struct['die_tag']

    @property
    def parent(self):
        return DIE(self.struct['die_parent'])

    @property
    def child(self):
        return DIE(self.struct['die_child'])

    @property
    def sibling(self):
        return DIE(self.struct['die_sib'])

    @property
    def siblings(self):
        result = [self]
        while True:
            sib = result[-1].sibling

            # Sibling lists are supposed to be circular lists, but it can
            # happen from time to time, for instance in the middle of the
            # type pruning pass, that we temporarily have a NULL-terminated
            # list: handle that for debug convenience.
            if not sib or sib == self:
                return result
            result.append(sib)

    @property
    def children(self):
        first_child = self.child
        return self.child.siblings if self.child else []

    @property
    def parents(self):
        """
        Return the whole parent chain starting from `self` (included).
        """
        p = self
        result = []
        while p:
            result.append(p)
            p = p.parent
        return result

    @property
    def attributes(self):
        vec = self.struct['die_attr']
        if not ptr_to_int(vec):
            return []
        vec = vec.dereference()
        num = int(vec['m_vecpfx']['m_num'])
        return [Attribute(vec['m_vecdata'][i])
                for i in range(num)]

    @property
    def iter_tree(self):
        """
        Yield all DIEs in self's subtree.
        """
        yield self
        for c in self.children:
            for ci in c.iter_tree:
                yield ci

    def find(self, predicate):
        """
        Return the list of all DIEs in the `self` subtree for which the
        `predicate` function returns true.
        """
        return [d for d in self.iter_tree if predicate(d)]

    @property
    def name(self):
        """
        If this DIE has a DW_AT_name attribute, return its string value.
        Otherwise, return None.
        """
        try:
            return self['DW_AT_name'].val
        except KeyError:
            return None

    def __repr__(self):
        if not self.value:
            return 'NULL'

        name = self.name
        name_repr = '{} '.format(name) if name else ''
        return '<{} {}{}>'.format(self.tag, name_repr, hex(self.address))


class Attribute(object):
    """
    Python wrapper around `dw_attr_struct` values to ease data access.
    """

    def __init__(self, value):
        if isinstance(value, basestring):
            value = gdb.parse_and_eval(value)
        self.value = value

    @property
    def attr(self):
        return self.value['dw_attr']

    @property
    def val_class(self):
        return self.value['dw_attr_val']['val_class']

    @property
    def val(self):
        val_class = self.val_class
        v = self.value['dw_attr_val']['v']
        if val_class == dw_val_class.dw_val_class_str:
            return v['val_str'].dereference()['str'].string()
        elif val_class == dw_val_class.dw_val_class_die_ref:
            return DIE(v['val_die_ref']['die'])
        else:
            raise NotImplementedError(str(val_class))

    def __repr__(self):
        try:
            val = self.val
        except NotImplementedError:
            val = self.val_class
        return '<{} {}>'.format(self.attr, val)


class DIEPrinter(object):
    name = 'dw_die_ref'
    pointed_name = 'die_struct'

    def __init__(self, value):
        self.value = value

    def to_string(self):
        return str(DIE(self.value))
