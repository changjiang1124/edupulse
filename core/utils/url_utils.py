from typing import Optional
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.sites.models import Site


def normalise_site_domain(domain: Optional[str]) -> str:
    """Return a bare hostname regardless of whether a scheme was stored."""
    cleaned = (domain or '').strip()
    if not cleaned:
        return ''

    parsed = urlsplit(cleaned if '://' in cleaned else f'https://{cleaned}')
    return (parsed.netloc or parsed.path).rstrip('/')


def get_site_protocol() -> str:
    """Return the configured site protocol without separators."""
    protocol = (getattr(settings, 'SITE_PROTOCOL', 'https') or 'https').strip().rstrip(':/')
    return protocol or 'https'


def get_public_site_domain() -> str:
    """Return the public-facing website domain used in customer-facing copy."""
    from core.models import OrganisationSettings

    org_settings = OrganisationSettings.get_instance()
    primary_domain = normalise_site_domain(getattr(org_settings, 'site_domain', ''))
    if primary_domain:
        return primary_domain

    configured_app_domain = normalise_site_domain(getattr(settings, 'SITE_DOMAIN', ''))
    if configured_app_domain:
        return configured_app_domain

    return normalise_site_domain(Site.objects.get_current().domain)


def get_app_domain() -> str:
    """Return the EduPulse application domain for authenticated/internal routes."""
    configured_app_domain = normalise_site_domain(getattr(settings, 'SITE_DOMAIN', ''))
    if configured_app_domain:
        return configured_app_domain

    site_domain = normalise_site_domain(Site.objects.get_current().domain)
    if site_domain:
        return site_domain

    return get_public_site_domain()


def build_absolute_url(path_or_url: str, *, app_domain: bool = False) -> str:
    """Build an absolute URL using the configured public or application domain."""
    value = (path_or_url or '').strip()
    if not value:
        return ''

    parsed = urlsplit(value)
    if parsed.scheme and parsed.netloc:
        return value

    if value.startswith('//'):
        return f"{get_site_protocol()}:{value}"

    if not value.startswith('/'):
        value = f'/{value}'

    domain = get_app_domain() if app_domain else get_public_site_domain()
    return f"{get_site_protocol()}://{domain}{value}"
