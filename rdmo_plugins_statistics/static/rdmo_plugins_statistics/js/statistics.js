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
    return label.length > maxLength
        ? `${label.slice(0, maxLength - 1)}...`
        : label
}

const getTimeChartRows = (statistics, filters) => {
    const groupedRows = new Map()

    statistics.day.rows.forEach((row) => {
        const date = row.key.slice(0, 10)

        if (filters.start && date < filters.start) {
            return
        }

        if (filters.end && date > filters.end) {
            return
        }

        const [year, month] = date.split('-')
        let period

        switch (filters.interval) {
            case 'year':
                period = `${year}-01-01`
                break

            case 'quarter': {
                const quarterStartMonth = Math.floor((Number(month) - 1) / 3) * 3 + 1

                period = `${year}-${String(quarterStartMonth).padStart(2, '0')}-01`
                break
            }

            case 'month':
                period = `${year}-${month}-01`
                break

            default:
                period = date
        }

        const currentRow = groupedRows.get(period)

        if (currentRow) {
            currentRow.value += row.value
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
            return statistics.rows
        },

        getDisplayLabel: (row) => {
            return row.label
        },

        getTickRotation: () => {
            return { min: 0, max: 90 }
        }
    }
}

const prepareChartData = (statisticsType, statistics, filters, container) => {
    const rows = statisticsType.getRows(statistics, filters)
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
                ctx.fillText(dataset.data[index], bar.x, bar.y - 5)
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

    if (storedInterval) {
        intervalSelect.value = storedInterval
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
        updateClearDatesButton(clearDatesButton, filters)
        updateChart()
    })

    endDateInput.addEventListener('change', () => {
        filters.end = endDateInput.value
        updateClearDatesButton(clearDatesButton, filters)
        updateChart()
    })

    clearDatesButton.addEventListener('click', () => {
        startDateInput.value = ''
        endDateInput.value = ''
        filters.start = ''
        filters.end = ''

        updateClearDatesButton(clearDatesButton, filters)
        updateChart()
    })
}

const createStatisticsChart = (container) => {
    const statisticsElement = document.getElementById(container.dataset.statisticsId)
    const chartElement = container.querySelector('.statistics-chart')
    const totalElement = container.querySelector('.statistics-total')
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

    const initialData = getPreparedData()

    updateTotal(totalElement, initialData.rows)

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
            responsive: true,
            maintainAspectRatio: false,

            layout: {
                padding: {
                    top: 20
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
                    title: {
                        display: true,
                        text: container.dataset.xAxisTitle
                    },

                    grid: {
                        display: false
                    },

                    ticks: {
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
                    beginAtZero: true,

                    title: {
                        display: true,
                        text: container.dataset.yAxisTitle
                    },

                    ticks: {
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
