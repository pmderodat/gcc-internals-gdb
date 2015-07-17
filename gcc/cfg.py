import gdb
import gdb.types

from gcc.utils import ptr_to_int


class BasicBlock(object):

    def __init__(self, value):
        if isinstance(value, basestring):
            value = gdb.parse_and_eval(value)

        if not isinstance(value, gdb.Value):
            raise ValueError('Invalid input: {}'.format(repr(value)))
        valtyp = value.type
        if (valtyp.name != 'basic_block' and
                (valtyp.code != gdb.TYPE_CODE_PTR or
                    valtyp.target().name != 'basic_block_def')):
            raise ValueError('Invalid basic block: {}'.format(valtyp))

        self.value = value

    @property
    def index(self):
        return int(self.value['index'])

    def __repr__(self):
        addr = ptr_to_int(self.value)
        if addr:
            return '<BasicBlock {} at {:#x}>'.format(self.index, addr)
        else:
            return 'nullptr'


class Edge(object):

    def __init__(self, value):
        if isinstance(value, basestring):
            value = gdb.parse_and_eval(value)

        if not isinstance(value, gdb.Value):
            raise ValueError('Invalid input: {}'.format(repr(value)))
        valtyp = value.type
        if (valtyp.name != 'edge' and
                (valtyp.code != gdb.TYPE_CODE_PTR or
                    valtyp.target().name != 'edge_def')):
            raise ValueError('Invalid edge: {}'.format(valtyp))

        self.value = value

    @property
    def source(self):
        return BasicBlock(self.value['src'])

    @property
    def destination(self):
        return BasicBlock(self.value['dest'])

    def __repr__(self):
        addr = ptr_to_int(self.value)
        if addr:
            return '<Edge from BB {} to BB {}>'.format(self.source.index,
                                                       self.destination.index)
        else:
            return 'nullptr'


class BasicBlockPrinter(object):
    name = 'basic_block'

    def __init__(self, value):
        self.value = value

    def to_string(self):
        return str(BasicBlock(self.value))


class EdgePrinter(object):
    name = 'edge'

    def __init__(self, value):
        self.value = value

    def to_string(self):
        return str(Edge(self.value))
