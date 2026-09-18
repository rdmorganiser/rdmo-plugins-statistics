from django.contrib.sites.models import Site

import rules


@rules.predicate
def is_site_manager(user) -> bool:
    if not user.is_authenticated:
        return False

    current_site = Site.objects.get_current()

    return user.role.manager.filter(pk=current_site.pk).exists()


rules.add_perm('statistics.view_statistics', is_site_manager)
