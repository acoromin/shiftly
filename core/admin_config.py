from django.contrib.admin.apps import AdminConfig


class TechnicalAdminConfig(AdminConfig):
    default_site = 'core.admin_site.TechnicalAdminSite'
