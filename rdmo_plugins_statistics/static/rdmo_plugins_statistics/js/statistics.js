const CUMULATIVE_CALCULATION = 'cumulative_count'

const TIME_INTERVALS = ['day', 'month', 'quarter', 'year']
const DEFAULT_TIME_INTERVAL = 'month'
const TIME_STORAGE_KEYS = {
    interval: 'rdmo-statistics-interval',
    start: 'rdmo-statistics-start',
    end: 'rdmo-statistics-end'
}

const TIME_PERIOD_LIMITS = {
    day: 31,
    month: 24,
    quarter: 20,
    year: 20
}

const CATEGORY_CHART_MIN_SIZE = 340
const CATEGORY_CHART_AXIS_SIZE = 80
const HORIZONTAL_CATEGORY_SIZE = 32
const VERTICAL_CATEGORY_SIZE = 40

const updateClearDatesButton = (button, filters) => {
    button.disabled = !filters.start && !filters.end && filters.interval === DEFAULT_TIME_INTERVAL
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
    const sourceRows = statistics[calculationName].day.rows
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

        hasData: (statistics, filters, container, rows) => {
            if (container.dataset.calculation === CUMULATIVE_CALCULATION) {
                return rows.some((row) => row.value > 0)
            }

            return statistics[container.dataset.calculation].day.rows.some((row) => (
                isDateInRange(row.key.slice(0, 10), filters)
            ))
        },

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
        getRows: (statistics) => [...statistics.rows],

        hasData: (_statistics, _filters, _container, rows) => rows.some((row) => row.value > 0),

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
        tickRotation: getLabelTickRotation(container, defaultTickRotation),
        hasData: statisticsType.hasData(statistics, filters, container, rows)
    }
}

const updateBarChart = (chart, preparedData) => {
    chart.data.labels = preparedData.displayLabels
    chart.data.datasets[0].label = chart.canvas.closest('[data-statistics-chart]').dataset.datasetLabel
    chart.data.datasets[0].data = preparedData.rows.map((row) => row.value)
    chart.data.datasets[0].statisticsRows = preparedData.rows
    chart.data.datasets[0].statisticsLabels = preparedData.displayLabels
    chart.options.scales.x.ticks.minRotation = preparedData.tickRotation.min
    chart.options.scales.x.ticks.maxRotation = preparedData.tickRotation.max

    chart.update()
}

const updateTotal = (element, rows, calculationName) => {
    if (element) {
        element.textContent = calculationName === CUMULATIVE_CALCULATION
            ? rows.at(-1)?.value || 0
            : rows.reduce((sum, row) => sum + row.value, 0)
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

const getBarChartDataset = (container, preparedData) => {
    return {
        label: container.dataset.datasetLabel,
        data: preparedData.rows.map((row) => row.value),
        statisticsRows: preparedData.rows,
        statisticsLabels: preparedData.displayLabels,
        backgroundColor: container.dataset.barColor,
        borderWidth: 0,
        barPercentage: 0.85,
        categoryPercentage: 0.85
    }
}

const getTooltipCallbacks = (container) => {
    return {
        title(items) {
            if (items.length === 0) {
                return ''
            }

            const item = items[0]
            const label = item.dataset.statisticsLabels[item.dataIndex]

            return `${container.dataset.rowAxisTitle}: ${label}`
        },

        label(item) {
            const row = item.dataset.statisticsRows[item.dataIndex]

            return `${container.dataset.datasetLabel}: ${row.value}`
        }
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
                displayColors: false,
                callbacks: getTooltipCallbacks(container)
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
                getBarChartDataset(container, preparedData)
            ]
        },

        plugins: [
            drawValueLabelsPlugin
        ],

        options: getChartOptions(container, preparedData, isHorizontal)
    })
}

const createChart = createBarChart

const isValidDateValue = (value) => {
    if (!value) {
        return false
    }

    const input = document.createElement('input')
    input.type = 'date'
    input.value = value

    return input.value === value
}

const getInitialFilterValue = (parameters, name, storageKey, validate, fallback) => {
    const parameter = parameters.get(name)

    if (validate(parameter)) {
        return parameter
    }

    const stored = localStorage.getItem(storageKey)

    return validate(stored) ? stored : fallback
}

const clearLegacyTimeFilters = () => {
    ['project', 'user', 'cumulative-user'].forEach((name) => {
        const key = `${name}-statistics-interval`
        localStorage.removeItem(key)
        localStorage.removeItem(`${key}-start`)
        localStorage.removeItem(`${key}-end`)
    })
}

const createTimeFilterControls = () => {
    const container = document.querySelector('[data-statistics-time-controls]')

    if (!container) {
        return null
    }

    const intervalSelect = container.querySelector('.statistics-interval')
    const startDateInput = container.querySelector('.statistics-start-date')
    const endDateInput = container.querySelector('.statistics-end-date')
    const clearDatesButton = container.querySelector('.statistics-clear-dates')
    const errorElement = container.querySelector('.statistics-date-error')
    const parameters = new URLSearchParams(window.location.search)
    const filters = {
        interval: getInitialFilterValue(
            parameters,
            'interval',
            TIME_STORAGE_KEYS.interval,
            (value) => TIME_INTERVALS.includes(value),
            DEFAULT_TIME_INTERVAL,
        ),
        start: getInitialFilterValue(
            parameters,
            'from',
            TIME_STORAGE_KEYS.start,
            isValidDateValue,
            '',
        ),
        end: getInitialFilterValue(
            parameters,
            'to',
            TIME_STORAGE_KEYS.end,
            isValidDateValue,
            '',
        )
    }
    const listeners = []
    let valid = true

    intervalSelect.value = filters.interval
    startDateInput.value = filters.start
    endDateInput.value = filters.end

    const updateValidity = () => {
        startDateInput.max = filters.end
        endDateInput.min = filters.start
        valid = !(filters.start && filters.end && filters.start > filters.end)

        startDateInput.setAttribute('aria-invalid', String(!valid))
        endDateInput.setAttribute('aria-invalid', String(!valid))
        errorElement.textContent = valid ? '' : container.dataset.invalidDateMessage
        errorElement.hidden = valid

        return valid
    }

    const persist = () => {
        localStorage.setItem(TIME_STORAGE_KEYS.interval, filters.interval)

        for (const name of ['start', 'end']) {
            if (filters[name]) {
                localStorage.setItem(TIME_STORAGE_KEYS[name], filters[name])
            } else {
                localStorage.removeItem(TIME_STORAGE_KEYS[name])
            }
        }
    }

    const updateUrl = () => {
        const url = new URL(window.location.href)
        url.searchParams.set('interval', filters.interval)

        for (const [name, value] of [['from', filters.start], ['to', filters.end]]) {
            if (value) {
                url.searchParams.set(name, value)
            } else {
                url.searchParams.delete(name)
            }
        }

        window.history.replaceState({}, '', url)
    }

    const notify = () => {
        updateValidity()
        updateClearDatesButton(clearDatesButton, filters)
        persist()
        updateUrl()
        listeners.forEach((listener) => listener())
    }

    intervalSelect.addEventListener('change', () => {
        filters.interval = intervalSelect.value
        notify()
    })

    startDateInput.addEventListener('change', () => {
        filters.start = startDateInput.value
        notify()
    })

    endDateInput.addEventListener('change', () => {
        filters.end = endDateInput.value
        notify()
    })

    clearDatesButton.addEventListener('click', () => {
        intervalSelect.value = DEFAULT_TIME_INTERVAL
        startDateInput.value = ''
        endDateInput.value = ''
        filters.interval = DEFAULT_TIME_INTERVAL
        filters.start = ''
        filters.end = ''
        notify()
    })

    updateValidity()
    updateClearDatesButton(clearDatesButton, filters)
    persist()
    updateUrl()
    clearLegacyTimeFilters()

    return {
        filters,
        isValid: () => valid,
        subscribe: (listener) => listeners.push(listener)
    }
}

const escapeCsvCell = (value) => {
    let text = String(value)

    if (typeof value === 'string' && /^[=+\-@\t\r]/.test(text)) {
        text = `'${text}`
    }

    return `"${text.replaceAll('"', '""')}"`
}

const sanitizeFilenamePart = (value) => {
    return String(value || '')
        .trim()
        .replace(/[<>:"/\\|?*\u0000-\u001f\u007f]/g, '-')
        .replace(/\s+/g, '-')
        .replace(/-+/g, '-')
        .replace(/^-+|-+$/g, '') || 'site'
}

const getChartExportFilename = (container, filters, extension) => {
    const siteName = sanitizeFilenamePart(container.dataset.siteName)
    const name = container.dataset.statisticsId
        .replace('-statistics-data', '')
    const mode = container.dataset.exportKey
        ? `-${container.dataset.exportKey}`
        : ''

    const range = filters.start || filters.end
        ? `${filters.start || 'start'}-${filters.end || 'end'}`
        : 'all'

    return filters.interval
        ? `${siteName}-statistics-${name}${mode}-${filters.interval}-${range}.${extension}`
        : `${siteName}-statistics-${name}.${extension}`
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
        .map((row) => row.map(escapeCsvCell).join(','))
        .join('\n')

    const blob = new Blob([csv], {
        type: 'text/csv;charset=utf-8'
    })

    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')

    link.href = url
    link.download = getChartExportFilename(container, filters, 'csv')
    link.click()

    URL.revokeObjectURL(url)
}

const downloadChartImage = (container, filters, chart) => {
    const link = document.createElement('a')

    link.href = chart.toBase64Image('image/png')
    link.download = getChartExportFilename(container, filters, 'png')
    link.click()
}

const renderDataTable = (tableBody, preparedData) => {
    const rows = preparedData.rows.map((row, index) => {
        const tableRow = document.createElement('tr')
        const labelCell = document.createElement('th')
        const valueCell = document.createElement('td')

        labelCell.scope = 'row'
        labelCell.textContent = preparedData.displayLabels[index]
        valueCell.textContent = row.value
        tableRow.append(labelCell, valueCell)

        return tableRow
    })

    tableBody.replaceChildren(...rows)
}

const styleStatisticsControls = () => {
    // Detect the loaded CSS, since both RDMO generations use core/base.html.
    const bootstrap5 = Boolean(getComputedStyle(document.documentElement)
        .getPropertyValue('--bs-body-font-family').trim())

    if (bootstrap5) {
        document.querySelectorAll('.statistics-page .btn-default').forEach((button) => {
            button.classList.replace('btn-default', 'btn-outline-secondary')
        })
        document.querySelectorAll('.statistics-interval').forEach((select) => {
            select.classList.replace('form-control', 'form-select')
        })
        document.querySelectorAll('.statistics-mode-toggle').forEach((button) => {
            button.classList.add('link')
        })
    }

    return bootstrap5 ? 'bi' : 'fa'
}

const applyTimeChartMode = (container, mode, nextMode) => {
    const cumulative = mode.calculation === CUMULATIVE_CALCULATION
    const button = container.querySelector('.statistics-mode-toggle')
    button.setAttribute('aria-pressed', String(cumulative))
    button.title = nextMode.action_label
    button.classList.remove('is-cumulative')
    if (cumulative) {
        button.classList.add('is-cumulative')
    }
    button.querySelector('.statistics-mode-icon').className =
        `statistics-mode-icon ${toggleIconPrefix} ${toggleIconPrefix}-toggle-${cumulative ? 'on' : 'off'}`

    container.dataset.calculation = mode.calculation
    container.dataset.datasetLabel = mode.dataset_label
    container.dataset.yAxisTitle = mode.y_axis_title
    container.dataset.emptyMessage = mode.empty_message
    container.dataset.exportKey = mode.export_key

    container.querySelector('.statistics-chart-y-axis-title').textContent = mode.y_axis_title
    container.querySelector('.statistics-value-heading').textContent = mode.dataset_label
    container.querySelector('.statistics-chart').setAttribute(
        'aria-label',
        `${container.dataset.chartTitle}: ${mode.label}`,
    )
}

const createStatisticsChart = (container, timeControls) => {
    const statisticsElement = document.getElementById(container.dataset.statisticsId)
    const chartElement = container.querySelector('.statistics-chart')
    const chartLayout = container.querySelector('.statistics-chart-layout')
    const totalElement = container.querySelector('.statistics-total')
    const exportButton = container.querySelector('.statistics-export-csv')
    const imageExportButton = container.querySelector('.statistics-export-image')
    const emptyElement = container.querySelector('.statistics-empty-message')
    const dataTable = container.querySelector('.statistics-data-table')
    const tableBody = dataTable.querySelector('tbody')
    const statistics = JSON.parse(statisticsElement.textContent)
    const modeButton = container.querySelector('.statistics-mode-toggle')
    const modes = modeButton
        ? JSON.parse(document.getElementById(modeButton.dataset.modesId).textContent)
        : []
    let modeIndex = 0

    const statisticsTypeName = container.dataset.statisticsType
    const statisticsType = statisticsTypes[statisticsTypeName]

    if (!statisticsType) {
        console.error(`Unknown statistics type: ${statisticsTypeName}`)
        return
    }

    const filters = statisticsTypeName === 'time' ? timeControls.filters : {}

    if (statisticsTypeName === 'time') {
        applyTimeChartMode(container, modes[0], modes[1])
    }

    const getPreparedData = () => {
        return prepareChartData(statisticsType, statistics, filters, container)
    }

    if (exportButton) {
        exportButton.addEventListener('click', () => {
            downloadCsv(container, filters, getPreparedData())
        })
    }

    const initialData = getPreparedData()
    const chart = createChart(chartElement, container, initialData)

    if (imageExportButton) {
        imageExportButton.addEventListener('click', () => {
            downloadChartImage(container, filters, chart)
        })
    }

    const render = () => {
        const isInvalid = statisticsTypeName === 'time' && !timeControls.isValid()

        if (isInvalid) {
            chartLayout.hidden = true
            dataTable.hidden = true
            emptyElement.hidden = true
            exportButton.disabled = true
            imageExportButton.disabled = true
            return
        }

        const preparedData = getPreparedData()

        chartLayout.hidden = !preparedData.hasData
        dataTable.hidden = !preparedData.hasData
        emptyElement.textContent = preparedData.hasData ? '' : container.dataset.emptyMessage
        emptyElement.hidden = preparedData.hasData
        exportButton.disabled = !preparedData.hasData
        imageExportButton.disabled = !preparedData.hasData

        if (preparedData.hasData) {
            updateBarChart(chart, preparedData)
        }

        updateTotal(totalElement, preparedData.rows, container.dataset.calculation)
        renderDataTable(tableBody, preparedData)

        if (statisticsTypeName === 'category' && container.dataset.chartType === 'bar') {
            setCategoryChartSize(container, preparedData.rows)
        }

    }

    if (statisticsTypeName === 'time') {
        timeControls.subscribe(render)
        modeButton.addEventListener('click', () => {
            modeIndex = 1 - modeIndex
            applyTimeChartMode(container, modes[modeIndex], modes[1 - modeIndex])
            render()
        })
    }

    render()
}

const toggleIconPrefix = styleStatisticsControls()
const timeControls = createTimeFilterControls()

document.querySelectorAll('[data-statistics-chart]').forEach((container) => {
    createStatisticsChart(container, timeControls)
})
