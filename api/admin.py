from django.contrib import admin
from .models import *

# Register your models here.

admin.site.register(Location)
admin.site.register(Contact)
admin.site.register(User)
admin.site.register(Task)
admin.site.register(TaskTemplate)
admin.site.register(DropBoxToken)

