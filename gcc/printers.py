import gdb


class GDBSubprinter(gdb.printing.SubPrettyPrinter):
    def __init__(self, cls):
        self.cls = cls
        super(GDBSubprinter, self).__init__(cls.name)

    def matches(self, val):
        return val.type.name == self.cls.name

    def instantiate(self, val):
        return self.cls(val)


class GDBPrettyPrinters(gdb.printing.PrettyPrinter):
    def __init__(self, name):
        super(GDBPrettyPrinters, self).__init__(name, [])

    def append(self, pretty_printer_cls):
        self.subprinters.append(GDBSubprinter(pretty_printer_cls))

    def __call__(self, val):
        for printer in self.subprinters:
            if printer.enabled and printer.matches(val):
                return printer.instantiate(val)
        return None
