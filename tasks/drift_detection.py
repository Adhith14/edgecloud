import sys
sys.path.append('.')

def detect_drift(rows):
    if len(rows) < 4:
        return -1
    for i in range(len(rows) - 3):
        if (rows[i]['mem_pct'] < rows[i + 1]['mem_pct'] and \
            rows[i]['error_rate'] < rows[i + 1]['error_rate'] and \
            rows[i + 1]['mem_pct'] < rows[i + 2]['mem_pct'] and \
            rows[i + 1]['error_rate'] < rows[i + 2]['error_rate'] and \
            rows[i + 2]['mem_pct'] < rows[i + 3]['mem_pct'] and \
            rows[i + 2]['error_rate'] < rows[i + 3]['error_rate']):
            return i
    return -1