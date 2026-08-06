# def get_time_statistics(statistics):

#     return {
#         'day': {
#           'rows': [
#               {
#                   'key': period.isoformat(),
#                   'label': period.isoformat(),
#                   'value': count,
#               }
#               for period, count in statistics
#           ],
#         },
#     }

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


def get_catalog_statistics(statistics):

    return {
        'rows': [
            {
                'key': catalog.id,
                'label': catalog.title,
                'value': catalog.count,
                **({'label_suffix': ' *'} if not catalog.available else {}),
            }
            for catalog in statistics
        ],
    }
