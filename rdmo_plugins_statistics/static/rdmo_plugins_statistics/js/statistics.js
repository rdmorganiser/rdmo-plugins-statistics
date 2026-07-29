const updateClearDatesButton = (button, filters) => {
    button.disabled = !filters.start && !filters.end
}

const getLabels = (data, interval) => {
    return data.labels.map((label) => {
        const [year, month, day] = label.slice(0, 10).split('-').map(Number)
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
    })
}

const getTickRotation = (interval) => {
    return interval === 'year' ? 0 : 90
}

const getFilteredChartData = (statistics, filters) => {
    const groupedData = new Map()
    const dayData = statistics.day

    dayData.labels.forEach((label, index) => {
        const date = label.slice(0, 10)

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
                const quarterStartMonth =
                    Math.floor((Number(month) - 1) / 3) * 3 + 1

                period = `${year}-${String(quarterStartMonth).padStart(2, '0')}-01`
                break
            }

            case 'month':
                period = `${year}-${month}-01`
                break

            default:
                period = date
        }

        const currentValue = groupedData.get(period) || 0

        groupedData.set(
            period,
            currentValue + dayData.values[index]
        )
    })

    return {
        labels: Array.from(groupedData.keys()),
        values: Array.from(groupedData.values())
    }
}

const updateBarChart = (chart, data, interval) => {
    const tickRotation = getTickRotation(interval)

    chart.data.labels = getLabels(data, interval)
    chart.data.datasets[0].data = data.values
    chart.options.scales.x.ticks.maxRotation = tickRotation
    chart.options.scales.x.ticks.minRotation = tickRotation

    chart.update()
}

const updateTotal = (element, data) => {
    element.textContent = data.values.reduce((sum, value) => sum + value, 0)
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
                ctx.fillText(
                    dataset.data[index],
                    bar.x,
                    bar.y - 5
                )
            })
        })

        ctx.restore()
    }
}

const createStatisticsChart = (container) => {
    const statisticsElement = document.getElementById(
        container.dataset.statisticsId
    )
    const intervalSelect = container.querySelector('.statistics-interval')
    const startDateInput = container.querySelector('.statistics-start-date')
    const endDateInput = container.querySelector('.statistics-end-date')
    const clearDatesButton = container.querySelector('.statistics-clear-dates')
    const totalElement = container.querySelector('.statistics-total')
    const chartElement = container.querySelector('.statistics-chart')

    const statistics = JSON.parse(statisticsElement.textContent)
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

    const initialData = getFilteredChartData(statistics, filters)

    updateClearDatesButton(clearDatesButton, filters)
    updateTotal(totalElement, initialData)

    const chart = new Chart(chartElement, {
        type: 'bar',

        data: {
            labels: getLabels(initialData, filters.interval),
            datasets: [
                {
                    label: container.dataset.datasetLabel,
                    data: initialData.values,
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
                        maxRotation: getTickRotation(filters.interval),
                        minRotation: getTickRotation(filters.interval)
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
        const data = getFilteredChartData(statistics, filters)

        updateBarChart(chart, data, filters.interval)
        updateTotal(totalElement, data)
    }

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

document.querySelectorAll('[data-statistics-chart]').forEach(
    createStatisticsChart
)
