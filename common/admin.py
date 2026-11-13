"""Django admin site for root-level configuration only."""

from django.contrib import admin


class SuperuserOnlyModelAdmin(admin.ModelAdmin):
    """Keep tenant data out of the global Django admin for scoped operators."""

    def has_module_permission(self, request):
        return request.user.is_superuser

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.none()

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
