from collections import Counter
from typing import List

def get_domain_from_email(email: str) -> str:
    return ".".join(email.split("@")[-1].split(".")[-2:])

def get_project_role_count(user, role) -> int:
    project_role_count = Counter(membership.role for membership in user.memberships.all())
    return project_role_count.get(role, 0)

def project_contains_test(project) -> bool:
    if not project.title and not project.description:
        return False
    title = project.title.lower()
    description = project.description.lower() if project.description else ""
    return "test" in title or "test" in description

