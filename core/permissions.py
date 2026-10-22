def is_technical_admin(user):
    return bool(
        user.is_authenticated and user.is_active and user.is_staff and user.is_superuser
    )
