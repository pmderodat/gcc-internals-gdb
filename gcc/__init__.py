import sys

import gdb


setup_done = False
init_done = False


def setup():
    global setup_done
    if setup_done:
        return
    setup_done = True

    gdb.events.new_objfile.connect(handle_new_objfile)


def handle_new_objfile(event):
    objfile = event.new_objfile
    if objfile.filename.split('/')[-1] not in (
        'cc1', 'cc1plus', 'gnat1', 'f951'
    ):
        return

    import gcc.cfg
    from gcc.cfg import BasicBlock, BasicBlockPrinter, Edge, EdgePrinter
    from gcc.commands import Pregset
    import gcc.ira
    from gcc.ira import (
        IRAAllocno, IRAAllocnoPrinter, IRAObject, IRAMove, IRAMovePrinter,
        IRALoopTreeNode
    )
    from gcc.matchers import MatchTree
    from gcc.printers import GDBPrettyPrinters, LocationPrinter
    from gcc.tracers import LocationDescriptionTracer
    from gcc.tree import TreePrinter, Tree
    import gcc.utils

    value_wrappers = [
        BasicBlock, Edge,
        IRAAllocno, IRAObject, IRAMove, IRALoopTreeNode,
        Tree
    ]

    # Create new commands only once...
    global init_done
    if not init_done:
        Pregset()
        MatchTree()
        LocationDescriptionTracer()
        for w in value_wrappers:
            setattr(sys.modules['__main__'], w.__name__, w)
        sys.modules['__main__'].fmt_list = gcc.utils.fmt_list
        sys.modules['__main__'].cfg = gcc.cfg
        sys.modules['__main__'].ira = gcc.ira
        init_done = True

    # ... and instanciate pretty-printers as many times as needed (once per
    # matching objfile).

    printers = GDBPrettyPrinters('gcc')
    printers.append(BasicBlockPrinter)
    printers.append(EdgePrinter)
    # TODO: these don't work right now because of input type matching.
    # printers.append(IRAAllocnoPrinter)
    # printers.append(IRAMovePrinter)
    printers.append(LocationPrinter)
    printers.append(TreePrinter)
    objfile.pretty_printers.append(printers)
