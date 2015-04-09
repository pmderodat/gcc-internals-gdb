import gdb

from gcc.tree import Tree


def iter_frames(start=None):
    if start is None:
        start = gdb.selected_frame()

    while start:
        yield start
        start = start.older()


class Tracer(object):
    def __init__(self):
        self.points_of_interest = []
        self.breakpoints = []
        self.enabled = False

    def add_breakpoint(self, spec, expr=None):
        bp = LocationDescriptionBreakpoint(spec, self, expr)
        bp.enabled = self.enabled
        self.points_of_interest.append(spec)
        self.breakpoints.append(bp)

    def set_enabling_state(self, state):
        self.enabled = state
        for bp in self.breakpoints:
            bp.enabled = state

    def enable(self):
        self.set_enabling_state(True)

    def disable(self):
        self.set_enabling_state(False)

    def is_frame_of_interest(self, frame):
        func_name = frame.name()
        for point in self.points_of_interest:
            if point in func_name:
                return True
        return False

    def add_trace(self, spec, data=None):
        level = len(list(
            frame
            for frame in iter_frames()
            if self.is_frame_of_interest(frame)
        ))
        data_suffix = ' ({})'.format(data) if data else ''
        gdb.write('{}{}{}\n'.format(
            '  ' * level, spec, data_suffix
        ))


class LocationDescriptionBreakpoint(gdb.Breakpoint):

    def __init__(self, spec, tracer, expr_computer=None):
        super(LocationDescriptionBreakpoint, self).__init__(
            spec, internal=True,
        )
        self.spec = spec
        self.tracer = tracer
        self.expr_computer = expr_computer

    def stop(self):
        data = None
        if self.expr_computer:
            try:
                data = self.expr_computer()
            except gdb.error as exc:
                data = '<{}: {}>'.format(type(exc), exc)
        self.tracer.add_trace(self.spec, data)
        return False


class LocationDescriptionTracer(gdb.Command):

    def __init__(self, name='gcc-trace-locdescr'):
        super(LocationDescriptionTracer, self).__init__(
            name, gdb.COMMAND_USER
        )
        self.name = name
        self.tracer = Tracer()

        self.tracer.add_breakpoint(
            'loc_list_from_tree_1', lambda: Tree('loc'))
        self.tracer.add_breakpoint(
            'function_to_dwarf_procedure', lambda: Tree('fndecl'))

        self.tracer.add_breakpoint(
            'type_byte_size', lambda: Tree('type'))

    def invoke(self, arg, from_tty):
        if not arg or arg == 'on':
            if self.tracer.enabled:
                raise gdb.GdbError(
                    'Traces for {} are already enabled'.format(self.name))
            self.tracer.enable()

        elif arg == 'off':
            if not self.tracer.enabled:
                raise gdb.GdbError(
                    'Traces for {} are not enabled yet'.format(self.name))
            self.tracer.disable()
