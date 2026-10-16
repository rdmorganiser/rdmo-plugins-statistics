"""Read explicitly selected project answers, which may contain personal data.

Each export column maps catalog URIs to their allowed attribute URIs. These
values are not anonymized by randomizing project IDs.
"""

from collections import defaultdict

from django.db.models import Q

from rdmo.projects.models import Value
from rdmo.questions.models import Question


def collect_project_values(projects, selectors):
    """Return named string joins for every project, using None outside selected catalogs."""
    columns = {
        column: collect_project_column(projects, catalog_selectors)
        for column, catalog_selectors in selectors.items()
    }
    return {
        project.pk: {column: values.get(project.pk) for column, values in columns.items()}
        for project in projects
    }


def collect_project_column(projects, selectors):
    """Return joined selected answers per eligible project; read no others."""
    catalog_projects = defaultdict(list)
    for project in projects:
        if project.catalog_id is not None and project.catalog.uri in selectors:
            catalog_projects[project.catalog.uri].append(project.pk)
    if not catalog_projects:
        return {}
    uris = {uri for catalog_uri in catalog_projects for uri in selectors[catalog_uri]}
    attribute_ids = dict(
        Question.objects.filter(attribute__uri__in=uris).order_by().values_list('attribute__uri', 'attribute_id')
    )
    selection = Q(pk__in=[])
    for catalog_uri, project_ids in catalog_projects.items():
        selection |= Q(
            project_id__in=project_ids,
            attribute_id__in=[attribute_ids[uri] for uri in selectors[catalog_uri] if uri in attribute_ids],
        )
    selected = {project_id: [] for project_ids in catalog_projects.values() for project_id in project_ids}
    values = (
        Value.objects.filter(selection, snapshot__isnull=True)
        .select_related('option').only('project_id', 'text', 'value_type', 'unit', 'file', 'option')
        .order_by('project_id', 'attribute__uri', 'set_prefix', 'set_index', 'collection_index', 'pk')
    )
    for value in values:
        text = str(value.value_and_unit)
        if text.strip():
            selected[value.project_id].append(text)
    return {project_id: ', '.join(texts) for project_id, texts in selected.items()}
