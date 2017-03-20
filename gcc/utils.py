import sys

import gdb


def iter_frames(start=None):
    """
    Iterate of frames starting at `start` (going to the oldest).

    If `start` is None, start from `gdb.newest_frame()`.
    """
    frame = start or gdb.newest_frame()
    while frame:
        yield frame
        frame = frame.older()


def chain_to_list(start, next_func, get_elt_func=None):
    """
    Turn a chain of nodes into a list.

    Fetch the chain tarting at `start` and following links calling
    next_func (`next = next_func(start)`). If `get_elt_func` is provided,
    return elements are mapped with it.
    """
    result = []
    while start:
        result.append(get_elt_func(start) if get_elt_func else start)
        start = next_func(start)
    return result


def fmt_list(lst):
    """Format a list to a string with one element per line."""
    return '\n'.join(
        str(item)
        for item in lst
    )


def ptr_to_int(value):
    return int(value.cast(gdb.lookup_type('intptr_t')))


class Enum(object):
    def __init__(self, gdb_type):
        self.gdb_type = gdb_type
        self.name_to_value = gdb.types.make_enum_dict(gdb_type)
        self.value_to_name = {
            value: name
            for name, value in self.name_to_value.items()
        }

    def __getattr__(self, name):
        return gdb.Value(self.name_to_value[name]).cast(self.gdb_type)


def is_string(value):
    """
    Python 2/3 compatibility helper. Return whether `value` is a string.
    """
    if sys.version_info.major <= 2:
        return isinstance(value, basestring)
    else:
        return isinstance(value, str)
