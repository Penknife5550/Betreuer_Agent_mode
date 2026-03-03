from django.contrib import admin

from apps.accounts.models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "phone", "created_at")
    list_filter = ("role", "schools")
    search_fields = ("user__username", "user__first_name", "user__last_name", "phone")
    raw_id_fields = ("user",)
    filter_horizontal = ("schools",)
