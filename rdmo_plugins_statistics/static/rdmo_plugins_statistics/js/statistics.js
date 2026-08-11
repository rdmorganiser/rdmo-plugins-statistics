const updateClearDatesButton = (button, filters) => {
    button.disabled = !filters.start && !filters.end
}

const getDateDisplayLabel = (row, interval) => {
    const [year, month, day] = row.key.slice(0, 10).split('-').map(Number)
    const date = new Date(year, month - 1, day)

    if (interval === 'year') {
        return year.toString()
    }

    if (interval === 'quarter') {
        const quarter = Math.floor((month - 1) / 3) + 1

        return `Q${quarter} ${year}`
    }

    if (interval === 'month') {
        return date.toLocaleDateString(undefined, {
            month: 'short',
            year: 'numeric'
        })
    }

    return date.toLocaleDateString(undefined, {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    })
}

const getLabelTickRotation = (container, defaultTickRotation) => {
    const orientation = container.dataset.labelOrientation

    if (orientation === 'vertical') {
        return { min: 90, max: 90 }
    }

    if (orientation === 'horizontal') {
        return { min: 0, max: 0 }
    }

    return defaultTickRotation
}

const truncateLabel = (label, maxLength = 20) => {
    const suffix = label.endsWith(' *') ? ' *' : ''
    const text = suffix ? label.slice(0, -suffix.length) : label

    return text.length > maxLength
        ? `${text.slice(0, maxLength - 3)}...${suffix}`
        : `${text}${suffix}`
}

const fillMissingPeriods = (rows, interval) => {
    if (rows.length === 0) {
        return rows
    }

    const rowsByKey = new Map(rows.map((row) => [row.key, row]))
    const result = []

    const current = new Date(`${rows[0].key}T00:00:00Z`)
    const end = new Date(`${rows.at(-1).key}T00:00:00Z`)

    while (current <= end) {
        const key = current.toISOString().slice(0, 10)

        result.push(
            rowsByKey.get(key) || {
                key,
                label: key,
                value: 0
            }
        )

        switch (interval) {
            case 'year':
                current.setUTCFullYear(current.getUTCFullYear() + 1)
                break

            case 'quarter':
                current.setUTCMonth(current.getUTCMonth() + 3)
                break

            case 'month':
                current.setUTCMonth(current.getUTCMonth() + 1)
                break

            default:
                current.setUTCDate(current.getUTCDate() + 1)
        }
    }

    return result
}

const timeCalculations = {
    period_count: {
        combine: (current, next) => current + next,
    },
    cumulative_count: {
        combine: (_current, next) => next,
    },
}

const getTimeChartRows = (statistics, filters, container) => {
    const groupedRows = new Map()

    const getPeriod = (date) => {
        const [year, month] = date.split('-')

        switch (filters.interval) {
            case 'year':
                return `${year}-01-01`

            case 'quarter': {
                const quarterStartMonth =
                    Math.floor((Number(month) - 1) / 3) * 3 + 1

                return `${year}-${String(quarterStartMonth).padStart(2, '0')}-01`
            }

            case 'month':
                return `${year}-${month}-01`

            default:
                return date
        }
    }

    statistics.day.rows.forEach((row) => {
        const date = row.key.slice(0, 10)

        if (filters.start && date < filters.start) {
            return
        }

        if (filters.end && date > filters.end) {
            return
        }

        const period = getPeriod(date)

        const calculation = timeCalculations[container.dataset.calculation]
        const currentRow = groupedRows.get(period)

        if (currentRow) {
                currentRow.value = calculation.combine(
                currentRow.value,
                row.value,
            )
        } else {
            groupedRows.set(period, {
                key: period,
                label: period,
                value: row.value
            })
        }
    })

    let rows = Array.from(groupedRows.values())

    if (container.dataset.fillGaps === 'true') {
        const startValue = (
            container.dataset.calculation === 'cumulative_count' &&
            filters.start
        )
            ? statistics.day.rows.reduce((value, row) => (
                row.key.slice(0, 10) < filters.start
                    ? row.value
                    : value
            ), 0)
            : 0

        const boundaries = [
            filters.start && {
                key: getPeriod(filters.start),
                value: startValue,
            },
            filters.end && {
                key: getPeriod(filters.end),
                value: 0,
            },
        ].filter(Boolean)

        boundaries.forEach(({ key, value }) => {
            if (!rows.some((row) => row.key === key)) {
                rows.push({
                    key,
                    label: key,
                    value,
                })
            }
        })

        rows.sort((a, b) => a.key.localeCompare(b.key))
        rows = fillMissingPeriods(rows, filters.interval)
    }

    if (container.dataset.calculation === 'cumulative_count') {
        let previousValue = 0

        rows = rows.map((row) => {
            if (row.value === 0) {
                return {
                    ...row,
                    value: previousValue,
                }
            }

            previousValue = row.value

            return row
        })
    }

    if (!filters.start && !filters.end) {
        const periodLimits = {
            day: 31,
            month: 24,
            quarter: 20,
            year: 20
        }

        return rows.slice(-periodLimits[filters.interval])
    }

    return rows
    }

const statisticsTypes = {
    time: {
        getRows: getTimeChartRows,

        getDisplayLabel: (row, filters) => {
            return getDateDisplayLabel(row, filters.interval)
        },

        getTickRotation: (filters) => {
            return filters.interval === 'year'
                ? { min: 0, max: 0 }
                : { min: 0, max: 90 }
        }
    },

    category: {
        getRows: (statistics) => {
            return [...statistics.rows].sort((a, b) => b.value - a.value)
        },

        getDisplayLabel: (row) => {
            return `${row.label}${row.label_suffix || ''}`
        },

        getTickRotation: () => {
            return { min: 0, max: 90 }
        }
    }
}

const prepareChartData = (statisticsType, statistics, filters, container) => {
    const rows = statisticsType.getRows(statistics, filters, container)
    const defaultTickRotation = statisticsType.getTickRotation(filters)

    return {
        rows,
        displayLabels: rows.map((row) => statisticsType.getDisplayLabel(row, filters)),
        tickRotation: getLabelTickRotation(container, defaultTickRotation)
    }
}

const updateBarChart = (chart, preparedData) => {
    chart.data.labels = preparedData.displayLabels
    chart.data.datasets[0].data = preparedData.rows.map((row) => row.value)
    chart.options.scales.x.ticks.minRotation = preparedData.tickRotation.min
    chart.options.scales.x.ticks.maxRotation = preparedData.tickRotation.max

    chart.update()
}

const updateTotal = (element, rows) => {
    if (element) {
        element.textContent = rows.reduce((sum, row) => sum + row.value, 0)
    }
}

const drawValueLabelsPlugin = {
    id: 'drawValueLabels',

    afterDatasetsDraw(chart) {
        const { ctx } = chart

        ctx.save()
        ctx.textAlign = 'center'
        ctx.textBaseline = 'bottom'
        ctx.font = '600 11px Arial'
        ctx.fillStyle = '#333'

        chart.data.datasets.forEach((dataset, datasetIndex) => {
            const meta = chart.getDatasetMeta(datasetIndex)

            meta.data.forEach((bar, index) => {
                const value = dataset.data[index]
                const isHorizontal = chart.options.indexAxis === 'y'

                if (isHorizontal) {
                    ctx.textAlign = 'left'
                    ctx.textBaseline = 'middle'
                    ctx.fillText(value, bar.x + 6, bar.y)
                } else {
                    ctx.textAlign = 'center'
                    ctx.textBaseline = 'bottom'
                    ctx.fillText(value, bar.x, bar.y - 5)
                }
            })
        })

        ctx.restore()
    }
}

const getTimeChartControls = (container) => {
    const intervalSelect = container.querySelector('.statistics-interval')
    const startDateInput = container.querySelector('.statistics-start-date')
    const endDateInput = container.querySelector('.statistics-end-date')
    const clearDatesButton = container.querySelector('.statistics-clear-dates')
    const storageKey = container.dataset.storageKey
    const storedInterval = localStorage.getItem(storageKey)
    const storedStart = localStorage.getItem(`${storageKey}-start`)
    const storedEnd = localStorage.getItem(`${storageKey}-end`)

    if (storedInterval) {
        intervalSelect.value = storedInterval
    }

    if (storedStart) {
        startDateInput.value = storedStart
    }

    if (storedEnd) {
        endDateInput.value = storedEnd
    }

    const filters = {
        interval: intervalSelect.value,
        start: startDateInput.value,
        end: endDateInput.value
    }

    updateClearDatesButton(clearDatesButton, filters)

    return {
        intervalSelect,
        startDateInput,
        endDateInput,
        clearDatesButton,
        storageKey,
        filters
    }
}

const addTimeChartListeners = (controls, updateChart) => {
    const {
        intervalSelect,
        startDateInput,
        endDateInput,
        clearDatesButton,
        storageKey,
        filters
    } = controls

    intervalSelect.addEventListener('change', () => {
        filters.interval = intervalSelect.value
        localStorage.setItem(storageKey, filters.interval)
        updateChart()
    })

    startDateInput.addEventListener('change', () => {
        filters.start = startDateInput.value
        localStorage.setItem(`${storageKey}-start`, filters.start)
        updateClearDatesButton(clearDatesButton, filters)
        updateChart()
    })

    endDateInput.addEventListener('change', () => {
        filters.end = endDateInput.value
        localStorage.setItem(`${storageKey}-end`, filters.end)
        updateClearDatesButton(clearDatesButton, filters)
        updateChart()
    })

    clearDatesButton.addEventListener('click', () => {
        startDateInput.value = ''
        endDateInput.value = ''
        filters.start = ''
        filters.end = ''

        localStorage.removeItem(`${storageKey}-start`)
        localStorage.removeItem(`${storageKey}-end`)
        updateClearDatesButton(clearDatesButton, filters)
        updateChart()
    })
}

const downloadCsv = (container, filters, preparedData) => {
    const isHorizontal = container.dataset.chartOrientation === 'horizontal'

    const headers = [
        isHorizontal
            ? container.dataset.yAxisTitle
            : container.dataset.xAxisTitle,
        container.dataset.datasetLabel
    ]

    const rows = preparedData.displayLabels.map((label, index) => [
        label,
        preparedData.rows[index].value
    ])

    const csvRows = [
        headers,
        ...rows
    ]

    const csv = csvRows
        .map((row) => (
            row
                .map((value) => `"${String(value).replaceAll('"', '""')}"`)
                .join(',')
        ))
        .join('\n')

    const name = container.dataset.statisticsId
        .replace('-statistics-data', '')

    const range = filters.start || filters.end
        ? `${filters.start || 'start'}-${filters.end || 'end'}`
        : 'all'

    const filename = filters.interval
        ? `statistics-${name}-${filters.interval}-${range}.csv`
        : `statistics-${name}.csv`

    const blob = new Blob([csv], {
        type: 'text/csv;charset=utf-8'
    })

    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')

    link.href = url
    link.download = filename
    link.click()

    URL.revokeObjectURL(url)
}

const createStatisticsChart = (container) => {
    const statisticsElement = document.getElementById(container.dataset.statisticsId)
    const chartElement = container.querySelector('.statistics-chart')
    const totalElement = container.querySelector('.statistics-total')
    const exportButton = container.querySelector('.statistics-export-csv')
    const statistics = JSON.parse(statisticsElement.textContent)

    const statisticsTypeName = container.dataset.statisticsType
    const statisticsType = statisticsTypes[statisticsTypeName]

    if (!statisticsType) {
        console.error(`Unknown statistics type: ${statisticsTypeName}`)
        return
    }

    const controls = statisticsTypeName === 'time'
        ? getTimeChartControls(container)
        : null

    const filters = controls?.filters || {}

    const getPreparedData = () => {
        return prepareChartData(statisticsType, statistics, filters, container)
    }

    if (exportButton) {
        exportButton.addEventListener('click', () => {
            downloadCsv(container, filters, getPreparedData())
        })
    }

    const initialData = getPreparedData()

    updateTotal(totalElement, initialData.rows)

    const isHorizontal = container.dataset.chartOrientation === 'horizontal'

    const chart = new Chart(chartElement, {
        type: 'bar',

        data: {
            labels: initialData.displayLabels,

            datasets: [
                {
                    label: container.dataset.datasetLabel,
                    data: initialData.rows.map((row) => row.value),
                    backgroundColor: container.dataset.barColor,
                    borderWidth: 0,
                    barPercentage: 0.85,
                    categoryPercentage: 0.85
                }
            ]
        },

        plugins: [
            drawValueLabelsPlugin
        ],

        options: {
            indexAxis: isHorizontal ? 'y' : 'x',
            responsive: true,
            maintainAspectRatio: false,

            layout: {
                padding: {
                    top: 20,
                    right: isHorizontal ? 30 : 0
                }
            },

            plugins: {
                legend: {
                    display: false
                },

                tooltip: {
                    displayColors: false
                }
            },

            scales: {
              x: {
                  beginAtZero: isHorizontal,

                  title: {
                      display: true,
                      text: container.dataset.xAxisTitle
                  },

                  grid: {
                      display: isHorizontal
                  },

                  ticks: isHorizontal
                      ? {
                          precision: 0
                      }
                      : {
                          minRotation: initialData.tickRotation.min,
                          maxRotation: initialData.tickRotation.max,

                          callback(value) {
                              const label = this.getLabelForValue(value)

                              return container.dataset.labelOrientation === 'vertical'
                                  ? truncateLabel(label)
                                  : label
                          }
                      }
              },

              y: {
                  beginAtZero: !isHorizontal,

                  title: {
                      display: true,
                      text: container.dataset.yAxisTitle
                  },

                  ticks: isHorizontal
                      ? {}
                      : {
                          precision: 0
                      }
              }
          }
        }
    })

    const updateChart = () => {
        const preparedData = getPreparedData()

        updateBarChart(chart, preparedData)
        updateTotal(totalElement, preparedData.rows)
    }

    if (controls) {
        addTimeChartListeners(controls, updateChart)
    }
}

document.querySelectorAll('[data-statistics-chart]').forEach(createStatisticsChart)
