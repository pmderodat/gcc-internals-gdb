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


def fmt_list(lst):
    """Format a list to a string with one element per line."""
    return '\n'.join(
        str(item)
        for item in lst
    )


def ptr_to_int(value):
    return int(value.cast(gdb.lookup_type('intptr_t')))
