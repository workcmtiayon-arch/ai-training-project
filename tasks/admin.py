from django.contrib import admin
from .models import Task

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'priority', 'is_done', 'session_key', 'created_at')
    list_filter = ('priority', 'is_done')
    search_fields = ('title', 'description')
