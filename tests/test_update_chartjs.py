import pytest

from scripts import update_chartjs


def test_update_chartjs_replaces_only_valid_downloads(monkeypatch, tmp_path):
    javascript = b'/*! Chart.js v4.5.1 | Released under the MIT License */'
    license_text = b'The MIT License (MIT)\nChart.js Contributors\n'
    downloads = {
        'https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js': javascript,
        'https://cdn.jsdelivr.net/npm/chart.js@4.5.1/LICENSE.md': license_text,
    }
    monkeypatch.setattr(update_chartjs, 'download', downloads.__getitem__)

    update_chartjs.update_chartjs('4.5.1', tmp_path)

    assert (tmp_path / 'chart.umd.min.js').read_bytes() == javascript
    assert (tmp_path / 'chart.LICENSE.md').read_bytes() == license_text

    monkeypatch.setattr(update_chartjs, 'download', lambda url: b'invalid')
    with pytest.raises(ValueError, match='JavaScript does not match'):
        update_chartjs.update_chartjs('4.5.2', tmp_path)
    assert (tmp_path / 'chart.umd.min.js').read_bytes() == javascript
    assert (tmp_path / 'chart.LICENSE.md').read_bytes() == license_text
