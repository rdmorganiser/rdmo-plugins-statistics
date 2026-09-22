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
    const context = vm.createContext({
        console, URL, URLSearchParams, Blob,
        getComputedStyle: () => ({ getPropertyValue: () => bootstrap5 ? ' system-ui ' : '' }),
        document: {
            documentElement: {},
            querySelector: () => null,
            querySelectorAll: (selector) => ({
                '.statistics-page .btn-default': [button],
                '.statistics-interval': [select],
                '.statistics-mode-toggle': [toggle],
            }[selector] || []),
            createElement: () => element(),
        },
    })
    vm.runInContext(source, context)
    return { context, button, select, toggle,
        ...vm.runInContext('({ applyTimeChartMode, createTimeFilterControls, downloadCsv })', context) }
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
        const { button, select, toggle, applyTimeChartMode } = load(bootstrap5)
        assert.ok(button.classList.contains(bootstrap5 ? 'btn-outline-secondary' : 'btn-default'))
        assert.ok(select.classList.contains(bootstrap5 ? 'form-select' : 'form-control'))
        assert.equal(toggle.classList.contains('link'), bootstrap5)
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

test('Reset restores monthly dates and storage without changing a cumulative mode', () => {
    const { context, createTimeFilterControls, applyTimeChartMode } = load(false)
    const container = element()
    for (const name of ['interval', 'start-date', 'end-date', 'clear-dates', 'date-error']) {
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
    container.querySelector('.statistics-start-date').value = '2026-03-01'
    container.querySelector('.statistics-start-date').listeners.change()
    assert.equal(controls.isValid(), false)
    let notifications = 0
    controls.subscribe(() => notifications++)
    container.querySelector('.statistics-clear-dates').listeners.click()
    assert.equal(controls.filters.interval, 'month')
    assert.equal(controls.filters.start, '')
    assert.equal(controls.filters.end, '')
    assert.equal(controls.isValid(), true)
    assert.equal(stored.get('rdmo-statistics-interval'), 'month')
    assert.equal(context.window.location.search, '?interval=month')
    assert.equal(notifications, 1)
    assert.equal(container.querySelector('.statistics-clear-dates').disabled, true)
    assert.equal(projects.dataset.calculation, 'cumulative_count')
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
    projects.dataset.xAxisTitle = 'Date of creation'
    for (const [index, mode] of modes.entries()) {
        applyTimeChartMode(projects, mode, modes[1 - index])
        downloadCsv(projects, { interval: 'month' }, { displayLabels: ['Jan 2026'], rows: [{ value: 2 }] })
        assert.equal(link.download, `statistics-project-${mode.export_key}-month-all.csv`)
        assert.equal(await blob.text(), `"Date of creation","${mode.dataset_label}"\n"Jan 2026","2"`)
    }
})
