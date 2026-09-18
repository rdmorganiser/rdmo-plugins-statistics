import argparse
import re
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import Request, urlopen

CHARTJS_DIR = (
    Path(__file__).resolve().parents[1]
    / 'rdmo_plugins_statistics/static/rdmo_plugins_statistics/js'
)
CHARTJS_URL = 'https://cdn.jsdelivr.net/npm/chart.js@{version}'
VERSION_PATTERN = re.compile(r'\d+\.\d+\.\d+')


def download(url):
    request = Request(url, headers={'User-Agent': 'rdmo-plugins-statistics vendor updater'})
    with urlopen(request, timeout=30) as response:
        return response.read()


def update_chartjs(version, target_dir=CHARTJS_DIR):
    if VERSION_PATTERN.fullmatch(version) is None:
        raise ValueError('Chart.js version must use the form MAJOR.MINOR.PATCH.')

    base_url = CHARTJS_URL.format(version=version)
    files = {
        'chart.umd.min.js': download(f'{base_url}/dist/chart.umd.min.js'),
        'chart.LICENSE.md': download(f'{base_url}/LICENSE.md'),
    }
    if f'Chart.js v{version}'.encode() not in files['chart.umd.min.js'][:500]:
        raise ValueError('Downloaded JavaScript does not match the requested Chart.js version.')
    if not all(marker in files['chart.LICENSE.md'] for marker in (b'MIT License', b'Chart.js Contributors')):
        raise ValueError('Downloaded Chart.js license is not the expected MIT license.')

    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='.chartjs-', dir=target_dir) as staging:
        staging = Path(staging)
        for name, content in files.items():
            (staging / name).write_bytes(content)
        for name in files:
            (staging / name).replace(target_dir / name)

    return tuple(target_dir / name for name in files)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Update the vendored Chart.js browser build and license.')
    parser.add_argument('version', help='Stable Chart.js version, for example 4.5.1.')
    options = parser.parse_args(argv)
    try:
        paths = update_chartjs(options.version)
    except (OSError, ValueError) as exc:
        parser.exit(1, f'error: {exc}\n')
    print(f'Updated Chart.js {options.version}:')
    for path in paths:
        print(f'  {path.relative_to(Path.cwd()) if path.is_relative_to(Path.cwd()) else path}')


if __name__ == '__main__':
    main()
