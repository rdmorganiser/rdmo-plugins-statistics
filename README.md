# rdmo-plugins-statistics

[![Python Versions](https://img.shields.io/pypi/pyversions/rdmo.svg?style=flat)](https://www.python.org/)
[![Django Versions](https://img.shields.io/pypi/frameworkversions/django/rdmo)](https://pypi.python.org/pypi/rdmo/)
[![License](https://img.shields.io/github/license/rdmorganiser/rdmo?style=flat)](https://github.com/rdmorganiser/rdmo/blob/master/LICENSE) \
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![CI Workflow Status](https://github.com/rdmorganiser/rdmo-plugins-statistics/actions/workflows/ci.yml/badge.svg)](https://github.com/rdmorganiser/rdmo-plugins-statistics/actions/workflows/ci.yml)

<!--- mdtoc: toc begin -->
1. [Synopsis](#synopsis)
2. [Setup](#setup)
<!--- mdtoc: toc end -->

## Synopsis

Export plugins for [RDMO](https://github.com/rdmorganiser/rdmo). This exports the statistics of the projects and users in an instance.

## Setup

Install the plugins in your RDMO virtual environment using pip (directly from GitHub):

```bash
python -m pip install git+https://github.com/rdmorganiser/rdmo-plugins-statistics
```

Add the `rdmo_plugins` to the `INSTALLED_APPS` in `config/settings/local.py`:

```python
from . import INSTALLED_APPS
INSTALLED_APPS = ["rdmo_plugins_statistics", *INSTALLED_APPS]
```

After restarting RDMO, the exports should be usable.


