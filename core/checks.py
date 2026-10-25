from django.core.checks import Error, Tags, register
from django.core.exceptions import ImproperlyConfigured

from .network import trusted_proxy_networks


@register(Tags.security)
def check_trusted_proxy_cidrs(app_configs, **kwargs):
    try:
        trusted_proxy_networks()
    except ImproperlyConfigured as exc:
        return [Error(str(exc), id='core.E001')]
    return []
