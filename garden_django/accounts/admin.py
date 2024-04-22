from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

# Import your custom user model
CustomUser = get_user_model()

class CustomUserAdmin(UserAdmin):
    # Add form to include fields in the admin interface
    fieldsets = UserAdmin.fieldsets + (
        (_('Additional Info'), {'fields': ( 'api_key', 'use_system_api_key')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (_('Additional Info'), {
            'classes': ('wide',),
            'fields': ( 'api_key', 'use_system_api_key'),
        }),
    )
    list_display = UserAdmin.list_display + ( 'api_key', 'use_system_api_key')

admin.site.register(CustomUser, CustomUserAdmin)