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

    from gcc.cfg import BasicBlock, BasicBlockPrinter, Edge, EdgePrinter
    from gcc.commands import Pregset
    from gcc.matchers import MatchTree
    from gcc.printers import GDBPrettyPrinters, LocationPrinter
    from gcc.tracers import LocationDescriptionTracer
    from gcc.tree import TreePrinter, Tree
    import gcc.utils

    # Create new commands only once...
    global init_done
    if not init_done:
        Pregset()
        MatchTree()
        LocationDescriptionTracer()
        sys.modules['__main__'].Tree = Tree
        sys.modules['__main__'].fmt_list = gcc.utils.fmt_list
        init_done = True

    # ... and instanciate pretty-printers as many times as needed (once per
    # matching objfile).

    printers = GDBPrettyPrinters('gcc')
    printers.append(BasicBlockPrinter)
    printers.append(EdgePrinter)
    printers.append(LocationPrinter)
    printers.append(TreePrinter)
    objfile.pretty_printers.append(printers)
