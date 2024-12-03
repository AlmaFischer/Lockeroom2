from django.urls import path, include
from . import views

urlpatterns = [
    # Otras rutas
    path('camera/ping/<str:camera_name>/', views.camera_ping, name='camera_ping'),
    path('accounts/', include('allauth.urls')),  # Esto maneja login, logout y demás
    path('profile/', views.profile, name='profile'),
    path('password_change/', views.password_change, name='password_change'),
    path('estadisticas/', views.estadisticas, name='estadisticas'),
    path('casilleros', views.casilleros_list, name='casilleros_list'),
    path('', views.home, name='home'),
    path('casilleros/<int:casillero_id>/', views.casillero_detail, name='casillero_detail'),
    path('cameras/', views.camera_list, name='camera_list'),
    path('cameras/<int:pk>/', views.camera_detail, name='camera_detail'),
    path('cameras/<int:pk>/ping/', views.camera_ping, name='camera_ping'),
]
#TODO list:
#Lo pingo aqui porque asi no se me pierde xd
#Mejorar Estadisticas
#Hacer toda la construccion del locker
#Armar todo xd
