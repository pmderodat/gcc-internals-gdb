import gdb
import gdb.types

from gcc.cfg import BasicBlock, Loop
from gcc.utils import iter_frames, ptr_to_int


class IRAAllocno(object):

    def __init__(self, value):
        if isinstance(value, basestring):
            value = gdb.parse_and_eval(value)

        if not isinstance(value, gdb.Value):
            raise ValueError('Invalid input: {}'.format(repr(value)))
        valtyp = value.type
        if (valtyp.name != 'ira_allocno_t' and
                (valtyp.code != gdb.TYPE_CODE_PTR or
                    valtyp.target().name != 'ira_allocno')):
            raise ValueError('Invalid IRA allocno: {}'.format(valtyp))

        self.value = value

    def __nonzero__(self):
        return bool(self.value)

    @property
    def num(self):
        return int(self.value['num'])

    @property
    def regno(self):
        return int(self.value['regno'])

    @property
    def hard_regno(self):
        return int(self.value['hard_regno'])

    @property
    def mode(self):
        return self.value['mode']

    @property
    def loop_tree_node(self):
        if self.value['loop_tree_node']:
            return IRALoopTreeNode(self.value['loop_tree_node'])
        else:
            return None

    @property
    def color_data(self):
        # Color data is available during the call to ira_color only
        for frame in iter_frames():
            if frame.name() == 'ira_color':
                break
        else:
            assert False, 'There is no bucket outside IRA coloring'

        color_data_type = gdb.lookup_type('allocno_color_data').pointer()
        return self.value['add_data'].cast(color_data_type)

    @property
    def objects(self):
        for i in range(self.value['num_objects']):
            parent_obj = IRAObject(self.value['objects'][i])
            for obj in parent_obj.items():
                yield obj

    @property
    def as_bucket(self):
        result = []
        node = self
        while node:
            result.append(node)
            node = IRAAllocno(node.color_data['next_bucket_allocno'])
        return result

    def __repr__(self):
        addr = ptr_to_int(self.value)
        if addr:
            return '<IRAAllocno {} reg:{}:{} hardreg:{} at {:#x}>'.format(
                self.num,
                self.regno, self.mode,
                self.hard_regno,
                addr
            )
        else:
            return 'nullptr'


class IRAMove(object):

    def __init__(self, value):
        if isinstance(value, basestring):
            value = gdb.parse_and_eval(value)

        if not isinstance(value, gdb.Value):
            raise ValueError('Invalid input: {}'.format(repr(value)))
        valtyp = value.type
        if (valtyp.name != 'move_t' and
                (valtyp.code != gdb.TYPE_CODE_PTR or
                    valtyp.target().name != 'move')):
            raise ValueError('Invalid move: {}'.format(valtyp))

        self.value = value

    @property
    def allocno_from(self):
        return IRAAllocno(self.value['from'])

    @property
    def allocno_to(self):
        return IRAAllocno(self.value['to'])

    @property
    def next(self):
        return IRAMove(self.value['next'])

    @property
    def as_list(self):
        result = []
        cur = self
        while cur.value:
            result.append(cur)
            cur = cur.next
        return result

    def __repr__(self):
        addr = ptr_to_int(self.value)
        if addr:
            return '<Move from {} to {}{}>'.format(
                self.allocno_from,
                self.allocno_to,
                '(has next)' if self.next.value else ''
            )
        else:
            return 'nullptr'


class IRAObject(object):

    def __init__(self, value):
        if isinstance(value, basestring):
            value = gdb.parse_and_eval(value)

        if not isinstance(value, gdb.Value):
            raise ValueError('Invalid input: {}'.format(repr(value)))
        valtyp = value.type
        if (valtyp.name != 'ira_object_t' and
                (valtyp.code != gdb.TYPE_CODE_PTR or
                    valtyp.target().name != 'ira_object')):
            raise ValueError('Invalid IRA object: {}'.format(valtyp))

        self.value = value

    @property
    def allocno(self):
        return IRAAllocno(self.value['allocno'])

    def items(self):
        ira_object_t = gdb.lookup_type('ira_object_t')
        if self.value['conflict_vec_p']:
            array = self.value['conflicts_array'].cast(ira_object_t)
            i = 0
            while array[i]:
                yield IRAObject(array[i])
                i += 1

        else:
            object_id_map = gdb.parse_and_eval('ira_object_id_map')
            elt_size = int(gdb.parse_and_eval('IRA_INT_BITS'))
            elt_type = gdb.lookup_type('uint{}_t'.format(elt_size))
            bitvec = self.value['conflicts_array'].cast(elt_type.pointer())
            first = self.value['min']
            last = self.value['max']

            for i in range(first, last + 1):
                bit_index = i - first
                word_index = bit_index / elt_size
                word_bit_index = word_index * elt_size
                word = bitvec[word_index]
                if (word >> word_bit_index) and 1:
                    yield IRAObject(object_id_map[i])

    def __repr__(self):
        if self.value:
            return '<IRAObject for allocno {} at {:#x}'.format(
                self.allocno.num,
                ptr_to_int(self.value)
            )
        else:
            return 'nullptr'


class IRALoopTreeNode(object):

    def __init__(self, value):
        if isinstance(value, basestring):
            value = gdb.parse_and_eval(value)

        if not isinstance(value, gdb.Value):
            raise ValueError('Invalid input: {}'.format(repr(value)))
        valtyp = value.type
        if (valtyp.name != 'ira_loop_tree_node_t' and
                (valtyp.code != gdb.TYPE_CODE_PTR or
                    valtyp.target().name != 'ira_loop_tree_node')):
            raise ValueError('Invalid IRA loop tree node: {}'.format(valtyp))

        self.value = value

    @property
    def bb(self):
        if self.value['bb']:
            return BasicBlock(self.value['bb'])
        else:
            return None

    @property
    def loop(self):
        if self.value['loop']:
            return Loop(self.value['loop'])
        else:
            return None

    @property
    def next(self):
        if self.value['next']:
            return IRALoopTreeNode(self.value['next'])
        else:
            return None

    @property
    def children(self):
        if self.value['children']:
            return IRALoopTreeNode(self.value['children'])
        else:
            return None

    @property
    def children_list(self):
        result = []
        child = self.children
        while child:
            result.append(child)
            child = child.next
        return result

    def __repr__(self):
        addr = ptr_to_int(self.value)
        if addr:
            content = ('for BB {} '.format(self.bb.index)
                       if self.bb else
                       'for loop {} '.format(self.loop.num))
        else:
            content = ''
        return '<IRALoopTreeNode {}at {:#x}>'.format(
            content, addr
        )

    def repr_tree(self):
        result = []

        def handle_node(node, indent):
            children = node.children_list
            if children:
                bb_children = []
                loop_children = []
                for c in children:
                    if c.bb:
                        bb_children.append(c)
                    else:
                        loop_children.append(c)
                bb_children.sort(key=lambda c: c.bb.index)
                loop_children.sort(key=lambda c: c.loop.num)

                result.append('{}Loop {}({:#x}): '.format(
                    indent, node.loop.num,
                    ptr_to_int(node.value)
                ))
                if bb_children:
                    result.append("BB's ")
                for i, c in enumerate(bb_children):
                    if i > 0:
                        result.append(', ')
                    result.append('{}({:#x})'.format(c.bb.index,
                                                     ptr_to_int(node.value)))
                result.append('\n')
                for c in loop_children:
                    handle_node(c, indent + '  ')
            else:
                result.append('(no loop) BB {}({:#x})'.format(
                    node.bb.index, ptr_to_int(node.value)
                ))

        handle_node(self, '')
        return ''.join(result)


class IRAAllocnoPrinter(object):
    name = 'ira_allocno'

    def __init__(self, value):
        self.value = value

    def to_string(self):
        return str(IRAAllocno(self.value))


class IRAMovePrinter(object):
    name = 'move'

    def __init__(self, value):
        self.value = value

    def to_string(self):
        return str(IRAMove(self.value))


def allocnos_for_regno(regno):
    allocnos = gdb.parse_and_eval('ira_allocnos')
    count = int(gdb.parse_and_eval('ira_allocnos_num'))
    result = []

    for i in range(count):
        a = allocnos[i]
        if not a:
            continue

        if int(a['regno']) == regno:
            result.append(IRAAllocno(a))

    return result
