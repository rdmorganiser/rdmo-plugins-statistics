def get_time_statistics(statistics, calculation):
    total = 0
    rows = []

    for period, count in statistics:
        if calculation == 'cumulative_count':
            total += count
            value = total
        else:
            value = count

        rows.append({
            'key': period.isoformat(),
            'label': period.isoformat(),
            'value': value,
        })

    return {
        'day': {
            'rows': rows,
        },
    }


def get_category_statistics(statistics):
    return {
        'rows': list(statistics),
    }
