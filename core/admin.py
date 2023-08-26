from django.contrib import admin

from .models import Greeting


@admin.register(Greeting)
class GreetingAdmin(admin.ModelAdmin):
    list_display = ("id", "greeting", "created_at")
    list_filter = ("created_at",)
    search_fields = ("greeting",)
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
