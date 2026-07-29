const projectStatistics = JSON.parse(
    document.getElementById('project-statistics-data').textContent
)

const intervalSelect = document.getElementById(
    'project-statistics-interval'
)

const storedInterval = localStorage.getItem(
    'project-statistics-interval'
)

if (storedInterval && projectStatistics[storedInterval]) {
    intervalSelect.value = storedInterval
}

const chartElement = document.getElementById(
    'project-statistics-chart'
)

// const getLabels = (interval) => {
//     const labels = projectStatistics[interval].labels

//     if (interval === 'year') {
//         return labels.map(label => new Date(label).getFullYear())
//     }

//     return labels
// }

const getLabels = (interval) => {
    const labels = projectStatistics[interval].labels

    return labels.map((label) => {
        const date = new Date(label)

        if (interval === 'year') {
            return date.getFullYear().toString()
        }

        if (interval === 'quarter') {
            const quarter = Math.floor(date.getMonth() / 3) + 1

            return `Q${quarter} ${date.getFullYear()}`
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

const valueLabelsPlugin = {
    id: 'valueLabels',

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

const initialInterval = intervalSelect.value
const initialData = projectStatistics[initialInterval]

const projectStatisticsChart = new Chart(chartElement, {
    type: 'bar',

    data: {
        labels: getLabels(initialInterval),
        datasets: [
            {
                label: 'Number of Projects',
                data: initialData.values,
                backgroundColor: '#7eafe0',
                borderWidth: 0,
                barPercentage: 0.85,
                categoryPercentage: 0.85
            }
        ]
    },

    plugins: [
        valueLabelsPlugin
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
                    text: 'Created'
                },

                grid: {
                    display: false
                },

                ticks: {
                    maxRotation: getTickRotation(initialInterval),
                    minRotation: getTickRotation(initialInterval)
                }
            },

            y: {
                beginAtZero: true,

                title: {
                    display: true,
                    text: 'Total number of projects'
                },

                ticks: {
                    precision: 0
                }
            }
        }
    }
})

intervalSelect.addEventListener('change', () => {
    const interval = intervalSelect.value

    localStorage.setItem(
      'project-statistics-interval',
      interval
    )
    const data = projectStatistics[interval]

    projectStatisticsChart.data.labels = getLabels(interval)
    projectStatisticsChart.data.datasets[0].data = data.values

    projectStatisticsChart.options.scales.x.ticks.maxRotation =
    getTickRotation(interval)

    projectStatisticsChart.options.scales.x.ticks.minRotation =
    getTickRotation(interval)

    projectStatisticsChart.update()
})
