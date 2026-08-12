const CUMULATIVE_CALCULATION = 'cumulative_count'

const TIME_PERIOD_LIMITS = {
    day: 31,
    month: 24,
    quarter: 20,
    year: 20
}

const CATEGORY_CHART_MIN_SIZE = 340
const CATEGORY_CHART_AXIS_SIZE = 80
const HORIZONTAL_CATEGORY_SIZE = 32
const VERTICAL_CATEGORY_SIZE = 64

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

const getPeriodKey = (date, interval) => {
    const [year, month] = date.split('-')

    switch (interval) {
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

const isDateInRange = (date, filters) => {
    return !(
        (filters.start && date < filters.start) ||
        (filters.end && date > filters.end)
    )
}

const timeCalculations = {
    period_count: {
        combine: (current, next) => current + next,
    },
    cumulative_count: {
        combine: (_current, next) => next,
    },
}

const groupTimeRows = (rows, filters, calculation) => {
    const groupedRows = new Map()

    rows.forEach((row) => {
        const date = row.key.slice(0, 10)

        if (!isDateInRange(date, filters)) {
            return
        }

        const period = getPeriodKey(date, filters.interval)
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

    return Array.from(groupedRows.values())
}

const getCumulativeStartValue = (rows, start) => {
    return rows.reduce((value, row) => (
        row.key.slice(0, 10) < start
            ? row.value
            : value
    ), 0)
}

const addTimeRangeBoundaries = (
    rows,
    sourceRows,
    filters,
    calculationName,
) => {
    const startValue = (
        calculationName === CUMULATIVE_CALCULATION &&
        filters.start
    )
        ? getCumulativeStartValue(sourceRows, filters.start)
        : 0

    const boundaries = [
        filters.start && {
            key: getPeriodKey(filters.start, filters.interval),
            value: startValue,
        },
        filters.end && {
            key: getPeriodKey(filters.end, filters.interval),
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

    return rows.sort((a, b) => a.key.localeCompare(b.key))
}

const carryCumulativeValues = (rows) => {
    let previousValue = 0

    return rows.map((row) => {
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

const getTimeChartRows = (statistics, filters, container) => {
    const calculationName = container.dataset.calculation
    const calculation = timeCalculations[calculationName]
    const sourceRows = statistics.day.rows
    let rows = groupTimeRows(sourceRows, filters, calculation)

    if (container.dataset.fillGaps === 'true') {
        rows = addTimeRangeBoundaries(
            rows,
            sourceRows,
            filters,
            calculationName,
        )
        rows = fillMissingPeriods(rows, filters.interval)
    }

    if (calculationName === CUMULATIVE_CALCULATION) {
        rows = carryCumulativeValues(rows)
    }

    if (!filters.start && !filters.end) {
        return rows.slice(-TIME_PERIOD_LIMITS[filters.interval])
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

const setCategoryChartSize = (container, rows) => {
    const chartContainer = container.querySelector('.statistics-chart-container')
    const isHorizontal = container.dataset.chartOrientation === 'horizontal'

    if (isHorizontal) {
        const height = Math.max(
            CATEGORY_CHART_MIN_SIZE,
            rows.length * HORIZONTAL_CATEGORY_SIZE + CATEGORY_CHART_AXIS_SIZE,
        )

        chartContainer.style.height = `${height}px`
    } else {
        const width = (
            rows.length * VERTICAL_CATEGORY_SIZE + CATEGORY_CHART_AXIS_SIZE
        )

        chartContainer.style.width = `${width}px`
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

const getChartDataset = (container, preparedData) => {
    return {
        label: container.dataset.datasetLabel,
        data: preparedData.rows.map((row) => row.value),
        backgroundColor: container.dataset.barColor,
        borderWidth: 0,
        barPercentage: 0.85,
        categoryPercentage: 0.85
    }
}

const getChartScales = (container, preparedData, isHorizontal) => {
    return {
        x: {
            beginAtZero: isHorizontal,

            grid: {
                display: isHorizontal
            },

            ticks: isHorizontal
                ? {
                    precision: 0
                }
                : {
                    minRotation: preparedData.tickRotation.min,
                    maxRotation: preparedData.tickRotation.max,

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

            ticks: isHorizontal
                ? {}
                : {
                    precision: 0
                }
        }
    }
}

const getChartOptions = (container, preparedData, isHorizontal) => {
    return {
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

        scales: getChartScales(container, preparedData, isHorizontal)
    }
}

const createBarChart = (chartElement, container, preparedData) => {
    const isHorizontal = container.dataset.chartOrientation === 'horizontal'

    return new Chart(chartElement, {
        type: 'bar',

        data: {
            labels: preparedData.displayLabels,
            datasets: [
                getChartDataset(container, preparedData)
            ]
        },

        plugins: [
            drawValueLabelsPlugin
        ],

        options: getChartOptions(container, preparedData, isHorizontal)
    })
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

    if (statisticsTypeName === 'category') {
        setCategoryChartSize(container, initialData.rows)
    }

    const chart = createBarChart(chartElement, container, initialData)

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
