from django.contrib import admin

from .models import Local

admin.site.register(Local)  # carga de locales; el CRUD de negocio queda para más adelante
