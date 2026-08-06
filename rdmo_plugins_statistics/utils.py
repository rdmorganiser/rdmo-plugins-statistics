def get_time_statistics(statistics):

    return {
        'day': {
          'rows': [
              {
                  'key': period.isoformat(),
                  'label': period.isoformat(),
                  'value': count,
              }
              for period, count in statistics
          ],
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
