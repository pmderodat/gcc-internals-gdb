import gdb


class Pregset(gdb.Command):
    def __init__(self, name='pregset'):
        super(Pregset, self).__init__(name, gdb.COMMAND_DATA,
                                      gdb.COMPLETE_SYMBOL)

    @property
    def inferior_printer(self):
        if not hasattr(self, '_inferior_printer'):
            self._inferior_printer = gdb.parse_and_eval('df_print_regset')
        return self._inferior_printer

    def invoke(self, arg, from_tty):
        val = gdb.parse_and_eval(arg)
        if val.type.name == 'bitmap_head':
            val = val.address
        if (val.type.code != gdb.TYPE_CODE_PTR or
                val.type.target().code not in (gdb.TYPE_CODE_TYPEDEF,
                                               gdb.TYPE_CODE_STRUCT) or
                val.type.target().name != 'bitmap_head'):
            gdb.write('Invalid type: {} (bitmap expected)'.format(
                str(val.type)))
            return
        self.inferior_printer(
            gdb.parse_and_eval('stderr'),
            val
        )
