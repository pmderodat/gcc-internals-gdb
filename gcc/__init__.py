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
    from gcc.matchers import MatchTree
    from gcc.printers import GDBPrettyPrinters
    from gcc.tree import TreePrinter, Tree

    # Create new commands only once...
    global init_done
    if not init_done:
        MatchTree()
        sys.modules['__main__'].Tree = Tree
        init_done = True

    # ... and instanciate pretty-printers as many times as needed (once per
    # matching objfile).

    objfile = event.new_objfile
    if objfile.filename.split('/')[-1] not in ('cc1', 'gnat1'):
        return

    printers = GDBPrettyPrinters('gcc')
    printers.append(TreePrinter)
    objfile.pretty_printers.append(printers)
