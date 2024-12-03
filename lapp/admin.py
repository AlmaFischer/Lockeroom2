# lockers/admin.py
from django.contrib import admin
from .models import  Casillero, Camera, LockerLog

admin.site.register(Casillero)
admin.site.register(Camera)
admin.site.register(LockerLog)
