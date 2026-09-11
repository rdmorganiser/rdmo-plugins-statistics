# Testing and development fixtures

Install the development dependencies from a source checkout:

```bash
pip install -e '.[dev]'
```

### Test users

Create site members with registration and last-login dates distributed across a
time range:

```bash
python manage.py runscript tests.scripts.bake_test_users \
    --script-args="--count 50 --seed 42 --batch-label september-users \
    --joined-start 2024-01-01T00:00:00+00:00 \
    --joined-end 2026-09-01T00:00:00+00:00 \
    --active-fraction 0.9 --last-login-fraction 0.7 \
    --manager-fraction 0.1 --editor-fraction 0.2"
```

The fractions independently control active accounts, staff status, last logins,
and RDMO manager, editor, and reviewer roles. Every generated user is a member of
the selected site. Use `--site-id` to select another site; otherwise the configured
current site is used. RDMO may additionally assign its current site through its
normal user-creation signal.

Usernames follow `test_BATCH_NUMBER`, email addresses use the reserved
`example.invalid` domain, and passwords are unusable. Existing usernames with the
same normalized batch prefix cause the script to stop before creating anything.
The script writes a JSON report containing IDs, usernames, dates, flags, and roles.
The whole user batch is created in one transaction.

The reusable function accepts the same controls:

```python
from tests.helpers import create_test_users

users = create_test_users(
    site=site,
    count=50,
    batch_label='september-users',
    seed=42,
    joined_between=(start_datetime, end_datetime),
    active_fraction=0.9,
    staff_fraction=0.05,
    manager_fraction=0.1,
    editor_fraction=0.2,
    reviewer_fraction=0.1,
    last_login_fraction=0.7,
)
```

### Test projects

The script uses an existing catalog and existing users belonging to
the selected site. It creates projects, explicit memberships, and current interview
values, then calculates progress with RDMO's answer tree:

```bash
python manage.py runscript tests.scripts.bake_test_projects \
    --script-args="--catalog-id 12 --owner alice --member bob:author \
    --count 100 --seed 42 --batch-label september-demo \
    --answer-fraction 0.2 0.9 --collection-size 1 3 \
    --created-start 2025-01-01T00:00:00+00:00 \
    --created-end 2026-09-01T00:00:00+00:00"
```

Use `--site-id` to select another site; otherwise the configured current site is
used. Repeat `--owner` to distribute ownership across users. Repeat `--member`
to assign additional `owner`, `manager`, `author`, or `guest` memberships. Owners
and additional members must not overlap. No users or catalogs are created.

The same implementation is available from Django shell or pytest:

```python
from tests.helpers import create_test_projects

reports = create_test_projects(
    catalog=catalog,
    site=site,
    owners=[alice],
    members=[(bob, 'author')],
    count=10,
    batch_label='interview-demo',
    seed=42,
    answer_fraction=1,
    collection_size=(1, 2),
    answer_overrides={
        # Keys are question URIs; values are Value field dictionaries.
        trigger_question.uri: {'text': 'yes'},
        choice_question.uri: {'option': option},
        dynamic_question.uri: {'text': 'Fixture label', 'external_id': 'fixture:1'},
    },
)
```

`fill_project_interview(project, ...)` also fills an existing empty project.
Overrides support `text`, `option`, and `external_id`, bypass automatic answer
selection, and are applied only when the question is visible. Supply semantically
valid payloads; overrides are not an interview-form validation API.

Ordinary scalar answers, static options, repeated pages/question sets, and repeated
questions are supported. Conditions are evaluated using RDMO and revisited for up
to 32 passes as answers reveal questions. Answers subsequently hidden by conditions
remain stored, as in a normal interview. File questions, dynamic-only option sets,
and options requiring additional input are reported as skipped unless a supported
explicit payload is supplied. No remote option providers are called or files created.

Answer fraction is a probability for attempting each eligible question location,
not a guaranteed progress percentage. JSON reports contain project IDs, value
counts, actual progress counts/totals, and skipped-question reasons. A seed makes
generated answer content reproducible for identical inputs/catalogs; IDs and
timestamps are not deterministic unless an explicit date range is provided.

Projects are labelled `[test:BATCH]`; an existing batch label on the site is
rejected. Each project is created in a transaction. If a later project fails,
earlier completed projects remain and can be identified by that batch label.
The script does not overwrite or delete existing projects.
