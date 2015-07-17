import gdb


def fmt_list(lst):
    """Format a list to a string with one element per line."""
    return '\n'.join(
        str(item)
        for item in lst
    )


def ptr_to_int(value):
    return int(value.cast(gdb.lookup_type('intptr_t')))
