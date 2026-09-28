// Run with: node --test tests/statistics.test.cjs (no npm dependencies).
const assert = require('node:assert/strict')
const { readFileSync } = require('node:fs')
const path = require('node:path')
const { test } = require('node:test')
const vm = require('node:vm')

const source = readFileSync(path.join(__dirname,
    '../rdmo_plugins_statistics/static/rdmo_plugins_statistics/js/statistics.js'), 'utf8')

const element = (classes = []) => {
    const names = new Set(classes)
    return {
        className: classes.join(' '),
        dataset: {}, attributes: {}, listeners: {}, children: {}, value: '',
        classList: {
            add: (name) => names.add(name),
            remove: (name) => names.delete(name),
            contains: (name) => names.has(name),
            replace: (from, to) => { if (names.delete(from)) names.add(to) },
        },
        setAttribute(name, value) { this.attributes[name] = value },
        addEventListener(name, handler) { this.listeners[name] = handler },
        querySelector(selector) { return this.children[selector] },
    }
}

const load = (bootstrap5) => {
    const button = element(['btn', 'btn-default'])
    const select = element(['form-control'])
    const toggle = element(['btn-link'])
    const projectIcon = element(['statistics-summary-icon', 'fa', 'fa-folder-o'])
    projectIcon.dataset.icon = 'folder2'
    const userIcon = element(['statistics-summary-icon', 'fa', 'fa-users'])
    userIcon.dataset.icon = 'people'
    const context = vm.createContext({
        console, URL, URLSearchParams, Blob, AbortController,
        getComputedStyle: () => ({ getPropertyValue: () => bootstrap5 ? ' system-ui ' : '' }),
        document: {
            documentElement: {},
            querySelector: () => null,
            querySelectorAll: (selector) => ({
                '.statistics-page .btn-default': [button],
                '.statistics-interval': [select],
                '.statistics-mode-toggle': [toggle],
                '.statistics-summary-icon': [projectIcon, userIcon],
            }[selector] || []),
            createElement: () => element(),
        },
    })
    vm.runInContext(source, context)
    return { context, button, select, toggle, projectIcon, userIcon,
        ...vm.runInContext('({ applyTimeChartMode, createTimeFilterControls, createProjectDateRangeControls, getTimeChartRows, prepareChartData, statisticsTypes, updateTotal, downloadCsv, downloadChartImage })', context) }
}

const chart = () => {
    const container = element()
    container.dataset.chartTitle = 'Projects over time'
    for (const selector of ['.statistics-mode-toggle', '.statistics-chart-y-axis-title',
        '.statistics-value-heading', '.statistics-chart', '.statistics-range-total-label']) {
        container.children[selector] = element()
    }
    const toggle = container.querySelector('.statistics-mode-toggle')
    toggle.setAttribute('aria-label', 'Cumulative projects')
    toggle.children['.statistics-mode-option-new'] = element()
    toggle.children['.statistics-mode-option-total'] = element()
    toggle.children['.statistics-mode-icon'] = element()
    container.querySelector('.statistics-range-total-label').textContent = 'Displayed'
    return container
}

const modes = ['new', 'total'].map((key) => ({
    calculation: key === 'new' ? 'period_count' : 'cumulative_count',
    label: `${key} projects`, action_label: `Show ${key} projects`,
    dataset_label: `Number of ${key} projects`, y_axis_title: `Number of ${key} projects`,
    empty_message: `No ${key} projects`, export_key: key,
}))

for (const bootstrap5 of [false, true]) {
    test(`Bootstrap ${bootstrap5 ? 5 : 3}: native controls and independent accessible toggles`, () => {
        const { button, select, toggle, projectIcon, userIcon, applyTimeChartMode } = load(bootstrap5)
        assert.ok(button.classList.contains(bootstrap5 ? 'btn-outline-secondary' : 'btn-default'))
        assert.ok(select.classList.contains(bootstrap5 ? 'form-select' : 'form-control'))
        assert.equal(toggle.classList.contains('link'), bootstrap5)
        assert.equal(projectIcon.className, bootstrap5
            ? 'statistics-summary-icon bi bi-folder2'
            : 'statistics-summary-icon fa fa-folder-o')
        assert.equal(userIcon.className, bootstrap5
            ? 'statistics-summary-icon bi bi-people'
            : 'statistics-summary-icon fa fa-users')
        const projects = chart()
        const users = chart()
        const projectToggle = projects.querySelector('.statistics-mode-toggle')
        const projectLabels = [
            projectToggle.querySelector('.statistics-mode-option-new'),
            projectToggle.querySelector('.statistics-mode-option-total'),
        ]
        projectLabels[0].textContent = 'New projects'
        projectLabels[1].textContent = 'Total projects'
        applyTimeChartMode(projects, modes[0], modes[1])
        applyTimeChartMode(users, modes[0], modes[1])
        applyTimeChartMode(projects, modes[1], modes[0])
        const control = projects.querySelector('.statistics-mode-toggle')
        assert.equal(control.attributes['aria-label'], 'Cumulative projects')
        assert.equal(control.attributes['aria-pressed'], 'true')
        assert.equal(control.title, 'Show new projects')
        assert.deepEqual(projectLabels.map((label) => label.textContent),
            ['New projects', 'Total projects'])
        assert.match(control.querySelector('.statistics-mode-icon').className,
            bootstrap5 ? /bi bi-toggle-on$/ : /fa fa-toggle-on$/)
        assert.equal(projects.dataset.exportKey, 'total')
        assert.equal(projects.querySelector('.statistics-value-heading').textContent, modes[1].dataset_label)
        assert.equal(projects.querySelector('.statistics-chart-y-axis-title').textContent, modes[1].y_axis_title)
        assert.equal(projects.querySelector('.statistics-range-total-label').textContent, 'Displayed')
        assert.equal(projects.querySelector('.statistics-chart').attributes['aria-label'],
            'Projects over time: total projects')
        assert.equal(users.dataset.calculation, 'period_count')
        applyTimeChartMode(projects, modes[0], modes[1])
        assert.equal(control.attributes['aria-pressed'], 'false')
        assert.equal(control.title, 'Show total projects')
        assert.match(control.querySelector('.statistics-mode-icon').className, /toggle-off$/)
        assert.equal(projects.querySelector('.statistics-range-total-label').textContent, 'Displayed')
    })
}

test('Dates clear independently and Reset restores defaults without changing a cumulative mode', () => {
    const { context, createTimeFilterControls, applyTimeChartMode } = load(false)
    const container = element()
    for (const name of [
        'interval', 'start-date', 'end-date', 'clear-start-date', 'clear-end-date', 'clear-dates', 'date-error'
    ]) {
        container.children[`.statistics-${name}`] = element()
    }
    const stored = new Map()
    context.localStorage = {
        getItem: (key) => stored.get(key),
        setItem: (key, value) => stored.set(key, value),
        removeItem: (key) => stored.delete(key),
    }
    context.window = {
        location: new URL('https://example.org/statistics/?interval=year&from=2025-01-01&to=2026-02-01'),
        history: { replaceState: (_state, _title, url) => { context.window.location = url } },
    }
    context.document.querySelector = () => container
    const projects = chart()
    applyTimeChartMode(projects, modes[1], modes[0])
    const controls = createTimeFilterControls()
    assert.equal(container.querySelector('.statistics-clear-start-date').disabled, false)
    assert.equal(container.querySelector('.statistics-clear-end-date').disabled, false)
    container.querySelector('.statistics-start-date').value = '2026-03-01'
    container.querySelector('.statistics-start-date').listeners.change()
    assert.equal(controls.isValid(), false)
    let notifications = 0
    controls.subscribe(() => notifications++)
    container.querySelector('.statistics-clear-start-date').listeners.click()
    assert.equal(controls.filters.start, '')
    assert.equal(controls.filters.end, '2026-02-01')
    assert.equal(controls.isValid(), true)
    assert.equal(stored.has('rdmo-statistics-start'), false)
    assert.equal(stored.get('rdmo-statistics-end'), '2026-02-01')
    assert.equal(context.window.location.search, '?interval=year&to=2026-02-01')
    assert.equal(container.querySelector('.statistics-clear-start-date').disabled, true)
    assert.equal(container.querySelector('.statistics-clear-end-date').disabled, false)
    container.querySelector('.statistics-clear-dates').listeners.click()
    assert.equal(controls.filters.interval, 'month')
    assert.equal(controls.filters.start, '')
    assert.equal(controls.filters.end, '')
    assert.equal(controls.isValid(), true)
    assert.equal(stored.get('rdmo-statistics-interval'), 'month')
    assert.equal(context.window.location.search, '?interval=month')
    assert.equal(notifications, 2)
    assert.equal(container.querySelector('.statistics-clear-end-date').disabled, true)
    assert.equal(container.querySelector('.statistics-clear-dates').disabled, true)
    assert.equal(projects.dataset.calculation, 'cumulative_count')
})

test('Cumulative project and user charts count only records in the selected range', async () => {
    const {
        context, applyTimeChartMode, getTimeChartRows, prepareChartData, statisticsTypes, updateTotal, downloadCsv,
    } = load(false)
    const counts = [
        ['2025-01-15', 5],
        ['2025-02-05', 2],
        ['2025-02-20', 3],
        ['2025-04-05', 4],
        ['2025-05-01', 1],
    ]
    let cumulative = 0
    const statistics = {
        period_count: { day: { rows: counts.map(([key, value]) => ({ key, value })) } },
        cumulative_count: { day: { rows: counts.map(([key, value]) => {
            cumulative += value
            return { key, value: cumulative }
        }) } },
    }
    const filters = { interval: 'month', start: '2025-02-10', end: '2025-04-30' }
    const projects = chart()
    applyTimeChartMode(projects, modes[1], modes[0])
    projects.dataset.fillGaps = 'true'

    const cumulativeRows = getTimeChartRows(statistics, filters, projects)
    assert.deepEqual(Array.from(cumulativeRows, ({ key, value }) => [key, value]), [
        ['2025-02-01', 3],
        ['2025-03-01', 3],
        ['2025-04-01', 7],
    ])
    const displayed = element()
    updateTotal(displayed, cumulativeRows, 'cumulative_count')
    assert.equal(displayed.textContent, 7)

    applyTimeChartMode(projects, modes[0], modes[1])
    const newRows = getTimeChartRows(statistics, filters, projects)
    assert.deepEqual(Array.from(newRows, ({ value }) => value), [3, 0, 4])
    updateTotal(displayed, newRows, 'period_count')
    assert.equal(displayed.textContent, 7)

    const users = element()
    users.dataset.calculation = 'cumulative_count'
    users.dataset.fillGaps = 'true'
    assert.equal(getTimeChartRows(statistics, filters, users).at(-1).value, 7)

    applyTimeChartMode(projects, modes[1], modes[0])
    projects.dataset.siteName = 'Example Site'
    projects.dataset.statisticsId = 'project-statistics-data'
    projects.dataset.xAxisTitle = 'Date of creation'
    projects.dataset.datasetLabel = 'Total number of projects'
    const preparedData = prepareChartData(statisticsTypes.time, statistics, filters, projects)
    let blob
    const link = { click() {} }
    context.URL = {
        createObjectURL: (value) => { blob = value; return 'blob:csv' },
        revokeObjectURL() {},
    }
    context.document.createElement = () => link
    downloadCsv(projects, filters, preparedData)
    assert.equal(link.download, 'Example-Site-statistics-project-total-month-2025-02-10-2025-04-30.csv')
    assert.match((await blob.text()).split('\n').at(-1), /,"7"$/)
})

test('Cumulative date boundaries handle empty, open, and gap-free ranges', () => {
    const { getTimeChartRows, statisticsTypes } = load(false)
    const statistics = {
        cumulative_count: { day: { rows: [
            { key: '2025-01-15', value: 5 },
            { key: '2025-02-20', value: 10 },
            { key: '2025-04-05', value: 14 },
        ] } },
    }
    const container = element()
    container.dataset.calculation = 'cumulative_count'
    container.dataset.fillGaps = 'true'

    const emptyFilters = { interval: 'month', start: '2025-03-01', end: '2025-03-31' }
    const emptyRows = getTimeChartRows(statistics, emptyFilters, container)
    assert.deepEqual(Array.from(emptyRows, ({ value }) => value), [0])
    assert.equal(statisticsTypes.time.hasData(statistics, emptyFilters, container, emptyRows), false)

    const toOnlyRows = getTimeChartRows(
        statistics, { interval: 'month', start: '', end: '2025-03-31' }, container,
    )
    assert.equal(toOnlyRows.at(-1).value, 10)
    const unfilteredRows = getTimeChartRows(
        statistics, { interval: 'month', start: '', end: '' }, container,
    )
    assert.equal(unfilteredRows.at(-1).value, 14)

    container.dataset.fillGaps = 'false'
    const withoutGaps = getTimeChartRows(
        statistics, { interval: 'month', start: '2025-02-10', end: '2025-04-30' }, container,
    )
    assert.deepEqual(Array.from(withoutGaps, ({ value }) => value), [5, 9])
})

const flushAsync = () => new Promise((resolve) => setImmediate(resolve))

const projectDateRangeHarness = (filters, fetchFunction) => {
    const container = element()
    container.dataset.projectDateRangeUrl = '/api/v1/statistics/projects/'
    const status = element()
    status.hidden = true
    status.dataset.loadingMessage = 'Updating'
    status.dataset.errorMessage = 'Could not update'
    container.children['.statistics-date-range-status'] = status

    const chartState = { catalog: null, progress: null, unavailable: false, resets: 0 }
    const charts = new Map([
        ['catalog', {
            reset: () => { chartState.catalog = null; chartState.unavailable = false; chartState.resets++ },
            setStatistics: (value) => { chartState.catalog = value; chartState.unavailable = false },
            setUnavailable: () => { chartState.unavailable = true },
        }],
        ['project-progress', {
            reset: () => { chartState.progress = null; chartState.unavailable = false; chartState.resets++ },
            setStatistics: (value) => { chartState.progress = value; chartState.unavailable = false },
            setUnavailable: () => { chartState.unavailable = true },
        }],
    ])
    const timeControls = {
        filters,
        valid: true,
        isValid() { return this.valid },
        subscribe(listener) { this.listener = listener },
    }

    return { container, status, chartState, timeControls,
        start: (createProjectDateRangeControls) => createProjectDateRangeControls(
            container, timeControls, charts, fetchFunction,
        ) }
}

test('Project date-range charts load on date changes and reset without a page reload', async () => {
    const { context, createProjectDateRangeControls } = load(false)
    context.window = { location: { href: 'https://example.org/statistics/' } }
    const requests = []
    const payload = {
        catalog: { rows: [{ label: 'Catalog', value: 2 }] },
        project_progress: { rows: [{ label: '50-59%', value: 2 }] },
    }
    const harness = projectDateRangeHarness(
        { start: '2025-01-01', end: '2025-01-31', interval: 'month' },
        async (url) => {
            requests.push(new URL(url))
            return { ok: true, json: async () => payload }
        },
    )

    harness.start(createProjectDateRangeControls)
    await flushAsync()
    assert.equal(requests.length, 1)
    assert.equal(requests[0].pathname, '/api/v1/statistics/projects/')
    assert.equal(requests[0].search, '?from=2025-01-01&to=2025-01-31')
    assert.equal(harness.chartState.catalog, payload.catalog)
    assert.equal(harness.chartState.progress, payload.project_progress)
    assert.equal(harness.status.hidden, true)

    harness.timeControls.filters.interval = 'year'
    harness.timeControls.listener()
    await flushAsync()
    assert.equal(requests.length, 1)

    harness.timeControls.filters.start = ''
    harness.timeControls.filters.end = ''
    harness.timeControls.listener()
    assert.equal(harness.chartState.resets, 2)
    assert.equal(harness.status.hidden, true)
})

test('Project date-range chart requests ignore stale results and report failures', async () => {
    const { context, createProjectDateRangeControls } = load(false)
    context.window = { location: { href: 'https://example.org/statistics/' } }
    const pending = []
    const harness = projectDateRangeHarness(
        { start: '2025-01-01', end: '', interval: 'month' },
        (url) => new Promise((resolve) => pending.push({ url: new URL(url), resolve })),
    )

    harness.start(createProjectDateRangeControls)
    harness.timeControls.filters.start = '2025-02-01'
    harness.timeControls.listener()
    pending[1].resolve({
        ok: true,
        json: async () => ({
            catalog: { rows: [{ label: 'February', value: 2 }] },
            project_progress: { rows: [] },
        }),
    })
    await flushAsync()
    pending[0].resolve({
        ok: true,
        json: async () => ({
            catalog: { rows: [{ label: 'January', value: 1 }] },
            project_progress: { rows: [] },
        }),
    })
    await flushAsync()
    assert.equal(harness.chartState.catalog.rows[0].label, 'February')

    harness.timeControls.filters.end = '2025-02-28'
    harness.timeControls.listener()
    pending[2].resolve({ ok: false, status: 500 })
    await flushAsync()
    assert.equal(harness.chartState.unavailable, true)
    assert.equal(harness.status.textContent, 'Could not update')
    assert.equal(harness.status.hidden, false)
})

test('CSV headers and filenames follow the selected chart mode', async () => {
    const { context, applyTimeChartMode, downloadCsv } = load(false)
    let blob
    const link = { click() {} }
    context.URL = {
        createObjectURL: (value) => { blob = value; return 'blob:csv' },
        revokeObjectURL() {},
    }
    context.document.createElement = () => link
    const projects = chart()
    projects.dataset.statisticsId = 'project-statistics-data'
    projects.dataset.siteName = 'Example Site'
    projects.dataset.xAxisTitle = 'Date of creation'
    for (const [index, mode] of modes.entries()) {
        applyTimeChartMode(projects, mode, modes[1 - index])
        downloadCsv(projects, { interval: 'month' }, { displayLabels: ['Jan 2026'], rows: [{ value: 2 }] })
        assert.equal(link.download, `Example-Site-statistics-project-${mode.export_key}-month-all.csv`)
        assert.equal(await blob.text(), `"Date of creation","${mode.dataset_label}"\n"Jan 2026","2"`)
    }
})

test('Category chart export filenames include the applied date range', async () => {
    const { context, downloadCsv } = load(false)
    let blob
    const link = { click() {} }
    context.URL = {
        createObjectURL: (value) => { blob = value; return 'blob:csv' },
        revokeObjectURL() {},
    }
    context.document.createElement = () => link
    const catalogs = chart()
    catalogs.dataset.statisticsId = 'catalog-statistics-data'
    catalogs.dataset.siteName = 'Example Site'
    catalogs.dataset.xAxisTitle = 'Catalog'
    catalogs.dataset.yAxisTitle = 'Number of projects'
    catalogs.dataset.chartOrientation = 'horizontal'
    catalogs.dataset.datasetLabel = 'Number of projects'

    downloadCsv(catalogs, { start: '2025-01-01', end: '2025-01-31' }, {
        displayLabels: ['Catalog A'], rows: [{ value: 2 }],
    })

    assert.equal(link.download, 'Example-Site-statistics-catalog-2025-01-01-2025-01-31.csv')
    assert.equal(await blob.text(), '"Number of projects","Number of projects"\n"Catalog A","2"')
})

test('PNG downloads use the active mode and chart filters', () => {
    const { context, applyTimeChartMode, downloadChartImage } = load(false)
    const link = { click() {} }
    context.document.createElement = () => link
    const projects = chart()
    projects.dataset.statisticsId = 'project-statistics-data'
    projects.dataset.siteName = 'Example Site'
    applyTimeChartMode(projects, modes[1], modes[0])

    let requestedType
    downloadChartImage(projects, {
        interval: 'month',
        start: '2026-01-01',
        end: '2026-03-31',
    }, {
        toBase64Image: (type) => {
            requestedType = type
            return 'data:image/png;base64,chart'
        },
    })

    assert.equal(requestedType, 'image/png')
    assert.equal(link.href, 'data:image/png;base64,chart')
    assert.equal(link.download, 'Example-Site-statistics-project-total-month-2026-01-01-2026-03-31.png')

    projects.dataset.siteName = 'Example / RDMO'
    downloadChartImage(projects, {}, {
        toBase64Image: () => 'data:image/png;base64,chart',
    })
    assert.equal(link.download, 'Example-RDMO-statistics-project.png')
})
