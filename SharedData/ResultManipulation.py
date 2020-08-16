

def get_port_result(used, unreachable, excluded, max_port: int):
    """
    Generates json-serializable dict from given lists.
    """
    # filtering excluded port outside range.
    excluded_in_range = [i for i in excluded if i <= max_port]

    closed_combined = set(used) | set(unreachable) | set(excluded_in_range)
    total = set(i for i in range(max_port + 1))

    result_all = {
        'Occupied': used,
        'Unreachable': unreachable,
        'Excluded': excluded_in_range,
        'Combined': list(closed_combined),
        'Available': list(total ^ closed_combined)
    }
    return result_all
