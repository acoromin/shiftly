from ipaddress import ip_address, ip_network

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def trusted_proxy_networks():
    try:
        trusted = tuple(ip_network(cidr, strict=False) for cidr in settings.TRUSTED_PROXY_CIDRS)
    except ValueError as exc:
        raise ImproperlyConfigured('TRUSTED_PROXY_CIDRS contiene una red no valida.') from exc
    if any(network.prefixlen == 0 for network in trusted):
        raise ImproperlyConfigured('No se puede confiar en todas las IP como proxies.')
    return trusted


def get_client_ip(request):
    try:
        peer = ip_address(request.META.get('REMOTE_ADDR', ''))
    except ValueError:
        return None
    trusted = trusted_proxy_networks()
    if not any(peer in network for network in trusted):
        return str(peer)

    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if not forwarded_for:
        return str(peer)
    hops = forwarded_for.split(',')
    if len(hops) > 20:
        return None
    try:
        addresses = [ip_address(hop.strip()) for hop in hops if hop.strip()]
    except ValueError:
        return None
    if len(addresses) != len(hops):
        return None
    for address in reversed(addresses):
        if not any(address in network for network in trusted):
            return str(address)
    return None
