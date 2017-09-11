import gdb


class GDBSubprinter(gdb.printing.SubPrettyPrinter):
    def __init__(self, cls):
        self.cls = cls
        super(GDBSubprinter, self).__init__(cls.name)

    def matches(self, val):
        if val.type.name == self.cls.name:
            return True

        pointed_name = getattr(self.cls, 'pointed_name', None)
        if (pointed_name is not None and
                val.type.code == gdb.TYPE_CODE_PTR and
                val.type.target().name == pointed_name):
            return True

        return False

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


class LocationPrinter(object):
    name = 'location_t'

    def __init__(self, value):
        self.value = value

    def to_string(self):
        expanded = gdb.parse_and_eval(
            'expand_location({})'.format(int(self.value))
        )
        return '{}:{}:{}'.format(
            expanded['file'].string() if expanded['file'] else '???',
            expanded['line'],
            expanded['column']
        )
