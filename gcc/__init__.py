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
    global init_done
    if init_done:
        return
    init_done = True
    objfile = event.new_objfile

    if objfile.filename.split('/')[-1] not in ('cc1', 'gnat1'):
        return

    from gcc.matchers import MatchTree
    from gcc.printers import GDBPrettyPrinters
    from gcc.tree import TreePrinter

    MatchTree()
    printers = GDBPrettyPrinters('gcc')
    printers.append(TreePrinter)
    objfile.pretty_printers.append(printers)
