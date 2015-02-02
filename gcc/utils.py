def fmt_list(lst):
    """Format a list to a string with one element per line."""
    return '\n'.join(
        str(item)
        for item in lst
    )
