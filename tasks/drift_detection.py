def detect_drift(rows):
    if len(rows) < 4:
        return -1
    for i in range(len(rows) - 2):
        prev_mem = rows[i]['mem_pct']
        prev_error = rows[i]['error_rate']
        next_next_mem = rows[i + 2]['mem_pct']
        next_next_error = rows[i + 2]['error_rate']
        if (rows[i + 1]['mem_pct'] > prev_mem and
            rows[i + 2]['mem_pct'] > next_next_mem and
            rows[i + 1]['error_rate'] > prev_error and
            rows[i + 2]['error_rate'] > next_next_error):
            return i + 1
    return -1