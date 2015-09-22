import os.path
import subprocess

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

    def _edge_vec_to_list(self, vec):
        if not vec:
            return []
        return [
            Edge(vec['m_vecdata'][i])
            for i in range(int(vec['m_vecpfx']['m_num']))
        ]

    @property
    def preds(self):
        return self._edge_vec_to_list(self.value['preds'])

    @property
    def succs(self):
        return self._edge_vec_to_list(self.value['succs'])

    @property
    def index(self):
        return int(self.value['index'])

    def __hash__(self):
        return hash(ptr_to_int(self.value))

    def __eq__(self, other):
        return self.value == other.value

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


class Loop(object):

    def __init__(self, value):
        if isinstance(value, basestring):
            value = gdb.parse_and_eval(value)

        if not isinstance(value, gdb.Value):
            raise ValueError('Invalid input: {}'.format(repr(value)))
        valtyp = value.type
        if (valtyp.code != gdb.TYPE_CODE_PTR or
                valtyp.target().name != 'loop'):
            raise ValueError('Invalid loop node: {}'.format(valtyp))

        self.value = value

    @property
    def num(self):
        return int(self.value['num'])

    @property
    def header(self):
        if self.value['header']:
            return BasicBlock(self.value['header'])
        else:
            return None

    @property
    def latch(self):
        if self.value['latch']:
            return BasicBlock(self.value['latch'])
        else:
            return None

    def __repr__(self):
        addr = ptr_to_int(self.value)
        if addr:
            header, latch = self.header, self.latch
            content = 'BB {} to {} '.format(
                header.index if header else '??',
                latch.index if latch else '??'
            )
        else:
            content = ''
        return '<Loop {} {}at {:#x}>'.format(self.num, content, addr)


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


def dump_dot(filename):
    lines = ['digraph cfg {']
    visited = set()

    def add_bb(bb):
        if bb in visited:
            return
        visited.add(bb)

        lines.append('bb_{index} [shape=box, label="BB {index}"];'.format(
            index=bb.index
        ))
        for edge in bb.succs:
            succ = edge.destination
            lines.append('bb_{} -> bb_{};'.format(
                bb.index, succ.index
            ))
            add_bb(succ)

    entry_bb = BasicBlock(gdb.parse_and_eval('cfun.cfg.x_entry_block_ptr'))
    add_bb(entry_bb)
    lines.append('}')

    dot = subprocess.Popen(
        ['dot', '-Tpng', '-o', filename],
        stdin=subprocess.PIPE
    )
    dot.communicate('\n'.join(lines))
    assert dot.returncode == 0
