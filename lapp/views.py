from django.shortcuts import render, get_object_or_404, redirect
from django.core.mail import EmailMessage
from django.conf import settings
from django.contrib.auth.models import User
from .forms import CasilleroPasswordForm
import json
from .models import Casillero, Camera, LockerLog, User
from lockers.mqtt_client import send_message
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from .forms import UserRegisterForm, UserLoginForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import render
from django.db.models import Count, F
from django.utils import timezone
from datetime import timedelta
from django.db.models.functions import TruncDate
from django.db.models import Max
from django.db.models import Subquery, OuterRef
from django.views.decorators.cache import never_cache
import matplotlib.pyplot as plt
import io
import urllib, base64
from django.core.cache import cache
from django.http import JsonResponse
@never_cache
@login_required
def estadisticas(request):
    user = request.user
    #SUPER USER:
    # Contar el total de casilleros
    total_casilleros = Casillero.objects.count()
    # Contar los casilleros ocupados
    casilleros_ocupados = Casillero.objects.filter(usuario__isnull=False).count()
    # Contar los casilleros disponibles
    casilleros_disponibles = total_casilleros - casilleros_ocupados
    # Contar la cantidad de usuarios
    total_usuarios = User.objects.count()
    # Contar la cantidad de controladores activos (cámaras con casilleros registrados)
    controladores_activos = Camera.objects.filter(casilleros__isnull=False).distinct().count()
    # Contar las aperturas totales de casilleros por día para los últimos 7 días
    fecha_hace_7_dias = timezone.now() - timedelta(days=7)
    aperturas_por_dia = LockerLog.objects.filter(
        event_type='open',
        timestamp__gte=fecha_hace_7_dias
    ).annotate(day=TruncDate('timestamp')).values('day').annotate(total_aperturas=Count('id')).order_by('day')
    # Otros 4 métricas adicionales que pueden ser de interés:
    # 1. Promedio de aperturas por casillero
    aperturas_promedio_por_locker = LockerLog.objects.filter(event_type='open').count() / total_casilleros if total_casilleros else 0
    # 2. Número de cámaras activas (que tienen casilleros asignados)
    total_camaras = Camera.objects.count()
    # 3. Casilleros por cámara (promedio)
    casilleros_por_camara_promedio = total_casilleros / total_camaras if total_camaras else 0
    # 4. Usuarios con más de un casillero
    usuarios_con_multiples_casilleros = Casillero.objects.values('usuario').annotate(casilleros_count=Count('id')).filter(casilleros_count__gt=1)
    #NORMAL USER:
    casilleros_usuario = Casillero.objects.filter(usuario=request.user)

    casilleros_por_usuario = Casillero.objects.values('usuario__username').annotate(casilleros_count=Count('id'))

    # Preparar los datos para el gráfico de torta
    usuarios = [item['usuario__username'] for item in casilleros_por_usuario]
    casilleros_count = [item['casilleros_count'] for item in casilleros_por_usuario]

    # Crear el gráfico de torta
    fig, ax = plt.subplots()
    ax.pie(casilleros_count, labels=usuarios, autopct='%1.1f%%', startangle=90, colors=["#1ABC9C", "#F4C542", "#E74C3C", "#2C3E50", "#1F3B4D"])
    ax.axis('equal')  # Para que el gráfico sea circular

    # Guardar la imagen del gráfico en un buffer en memoria
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)

    # Codificar la imagen a base64 para enviarla al template
    graph_url = base64.b64encode(buf.getvalue()).decode('utf-8')
    buf.close()
    

    # Aperturas totales por día
    aperturas_usuario_por_dia = LockerLog.objects.filter(
        user=user,
        event_type='open',
        timestamp__gte=fecha_hace_7_dias
    ).annotate(
        day=TruncDate('timestamp')
    ).values('day').annotate(
        total_aperturas=Count('id')
    ).order_by('day')

    # Casillero con más aperturas
    casillero_mas_aperturas = LockerLog.objects.filter(
        user=user,
        event_type='open'
    ).values(
        'locker__locker_id'
    ).annotate(
        total_aperturas=Count('id')
    ).order_by('-total_aperturas').first()

    # Casillero con más tiempo cerrado
    casillero_mas_tiempo_cerrado = Casillero.objects.filter(
    usuario=user
    ).annotate(
    last_opened=Subquery(
        LockerLog.objects.filter(
            locker=OuterRef('pk'),  # Relacionar con el casillero actual
            event_type='open'  # Solo considerar aperturas
        ).order_by('-timestamp')  # Ordenar por la más reciente
        .values('timestamp')[:1]  # Tomar la última apertura
    )
    ).order_by('last_opened').first()

    # Casillero con más tiempo ocupado
    casillero_mas_tiempo_ocupado = Casillero.objects.filter(
        usuario=user
    ).annotate(
        tiempo_ocupado=F('usuario__date_joined')  # Tiempo basado en asignación
    ).order_by('usuario__date_joined').first()

    
    context = {
        'aperturas_usuario_por_dia': aperturas_usuario_por_dia,
        'casillero_mas_aperturas': casillero_mas_aperturas,
        'casillero_mas_tiempo_cerrado': casillero_mas_tiempo_cerrado,
        'casillero_mas_tiempo_ocupado': casillero_mas_tiempo_ocupado,
        'total_casilleros': total_casilleros,
        'casilleros_ocupados': casilleros_ocupados,
        'casilleros_disponibles': casilleros_disponibles,
        'total_usuarios': total_usuarios,
        'controladores_activos': controladores_activos,
        'aperturas_por_dia': aperturas_por_dia,
        'aperturas_promedio_por_locker': aperturas_promedio_por_locker,
        'total_camaras': total_camaras,
        'casilleros_por_camara_promedio': casilleros_por_camara_promedio,
        'usuarios_con_multiples_casilleros': usuarios_con_multiples_casilleros,
        'grafico_casilleros_por_usuario': graph_url,
    }

    return render(request, 'estadisticas.html', context)
@never_cache
@login_required
def password_change(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()  # Guardar el nuevo cambio de contraseña
            update_session_auth_hash(request, form.user)  # Mantener al usuario autenticado después de cambiar la contraseña
            return redirect('profile')  # Redirigir a la página de perfil
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'password_change.html', {'form': form})
# Vista para mostrar y editar el perfil del usuario
@never_cache
@login_required
def profile(request):
    user = request.user  # Obtener el usuario actual

    if request.method == 'POST':
        form = UserChangeForm(request.POST, instance=user)  # Formulario para editar usuario
        if form.is_valid():
            form.save()  # Guardar los cambios
            return redirect('profile')  # Redirigir a la vista de perfil después de guardar los cambios
    else:
        form = UserChangeForm(instance=user)  # Mostrar el formulario con los datos actuales

    return render(request, 'profile.html', {'form': form})  # Renderizar la plantilla con el formulario
@never_cache
@login_required
def home(request):
    return render(request, 'home.html')
@never_cache
@login_required
def mqtt_message_received(request):
    # Handle received MQTT messages here
    return HttpResponse("Received MQTT message!")
@never_cache
@login_required
# Vista para mostrar el estado de los casilleros
def casilleros_list(request):
    # Verificar si el usuario es un superusuario
    if request.user.is_superuser:
        # Si es superusuario, mostrar todos los casilleros
        casilleros = Casillero.objects.select_related('usuario').all()
    else:
        # Si no es superusuario, solo mostrar los casilleros asignados al usuario
        casilleros = Casillero.objects.filter(usuario=request.user)

    return render(request, 'casilleros_list.html', {'casilleros': casilleros})
@never_cache
@login_required

def casillero_detail(request, casillero_id):
    casillero = get_object_or_404(Casillero, id=casillero_id)
    usuarios = User.objects.all()  # Obtén todos los usuarios para mostrarlos en el formulario

    # Si el usuario no es superusuario, solo puede cambiar la contraseña de su propio casillero
    if not request.user.is_superuser and casillero.usuario != request.user:
        return redirect('home')  # Redirige si no tiene permiso

    form = CasilleroPasswordForm(instance=casillero)  # Define el formulario por defecto

    if request.method == 'POST':
        # Si se presionó el botón para cambiar la contraseña
        if 'cambiar_contraseña' in request.POST:
            form = CasilleroPasswordForm(request.POST, instance=casillero)
            if form.is_valid():
                form.save()  # Guarda la nueva contraseña

                # Enviar correo electrónico notificando el cambio de contraseña
                usuario = casillero.usuario
                if usuario and usuario.username and usuario.email:
                    asunto = 'Tu contraseña ha sido cambiada'
                    mensaje = f"<p>Hola {usuario.username}, tu contraseña ha sido cambiada con éxito.</p><p>Tu nueva contraseña es: {casillero.password}</p>"
                    destinatarios = [usuario.email]

                    email = EmailMessage(
                        asunto,
                        mensaje,
                        settings.DEFAULT_FROM_EMAIL,
                        destinatarios,
                    )
                    email.content_subtype = "html"
                    email.send()

                # Publicar el mensaje MQTT en el tópico 'set_locker_pw'
                mqtt_message = {
                    "cam_target": casillero.camera.name,
                    "id": casillero.locker_id[-1],
                    "password": casillero.password
                }
                send_message("set_locker_g15", json.dumps(mqtt_message))  # Publicar el mensaje con JSON

                return redirect('casillero_detail', casillero_id=casillero.id)

        # Si se presionó el botón para cambiar el usuario (solo para superusuarios)
        elif 'cambiar_usuario' in request.POST and request.user.is_superuser:
            nuevo_usuario_id = request.POST.get('nuevo_usuario_id')
            if nuevo_usuario_id:
                nuevo_usuario = User.objects.get(id=nuevo_usuario_id)  # Obtener el nuevo usuario
                casillero.usuario = nuevo_usuario  # Asignar el nuevo usuario
                casillero.save()  # Guardar el casillero con el nuevo usuario

                # Enviar correo electrónico al nuevo usuario notificando el ID del casillero y su contraseña
                asunto = 'Nuevo Casillero Asignado'
                mensaje = f"""
                <p>Hola {nuevo_usuario.username},</p>
                <p>Se te ha asignado el Casillero ID: {casillero.locker_id}.</p>
                <p>Tu contraseña es: {casillero.password}</p>
                """
                destinatarios = [nuevo_usuario.email]

                email = EmailMessage(
                    asunto,
                    mensaje,
                    settings.DEFAULT_FROM_EMAIL,
                    destinatarios,
                )
                email.content_subtype = "html"
                email.send()

                # Actualizar el casillero después del cambio de usuario
                casillero.refresh_from_db()  # Refrescar la instancia de casillero desde la base de datos

                return redirect('casillero_detail', casillero_id=casillero.id)

        elif 'abrir_casillero' in request.POST:
            if request.user.is_superuser:
                mqtt_message = {
                    "cam_target": casillero.camera.name,  # Nombre de la cámara asociada
                    "id": casillero.locker_id[-1],  # ID del casillero (último carácter del ID)
                    "admin": "True",
                    "use_cam": "False",
                    "password": "",  # Nueva contraseña
                    "action": "open"
                }
                send_message("locker_action_g15", json.dumps(mqtt_message))
            else:
                #LOGICA DE ABRIR EL CASILLERO CON UNA PASSWORD
                mqtt_message = {
                    "cam_target": casillero.camera.name,  # Nombre de la cámara asociada
                    "id": casillero.locker_id[-1],  # ID del casillero (último carácter del ID)
                    "admin": "False",
                    "use_cam": "False",
                    "password": "",  # CONTRASEÑA PARA ABRIR EL CASILLERO
                    "action": "open"
                }

                send_message("locker_action_g15", json.dumps(mqtt_message))

        elif 'cerrar_casillero' in request.POST:
            if request.user.is_superuser:
                mqtt_message = {
                    "cam_target": casillero.camera.name,  # Nombre de la cámara asociada
                    "id": casillero.locker_id[-1],  # ID del casillero (último carácter del ID)
                    "admin": "True",
                    "use_cam": "False",
                    "password": "",  # Nueva contraseña
                    "action": "close"
                }
                send_message("locker_action_g15", json.dumps(mqtt_message))
        elif 'abrir_casillero_cam' in request.POST:
            mqtt_message = {
                    "cam_target": casillero.camera.name,  # Nombre de la cámara asociada
                    "id": casillero.locker_id[-1],  # ID del casillero (último carácter del ID)
                    "admin": "False",
                    "use_cam": "True",
                    "password": "",
                    "action": "open"
                }
            send_message("locker_action_g15", json.dumps(mqtt_message))

    return render(request, 'casillero_detail.html', {
        'casillero': casillero,
        'form': form,
        'usuarios': usuarios,  # Solo será útil si el usuario es superusuario
    })


def camera_list(request):

    """
    Lista todas las cámaras disponibles.
    """
    cameras = Camera.objects.all()  # Recuperar las cámaras de la base de datos
    camera_status = {}


    # Comprobar el estado del ping desde el cache
    for camera in cameras:
        #camera.css_class = "text-success" if camera.is_ping else "text-danger"
        # Recuperamos el estado del ping del cache
        status = cache.get(camera.name, False)
        camera_status[camera.name] = status
        camera.check_ping()

    return render(request, 'camera_list.html', {'cameras': cameras, 'camera_status': camera_status})

def camera_detail(request, pk):
    """
    Muestra los detalles de una cámara específica.
    """
    camera = get_object_or_404(Camera, pk=pk)
    return render(request, 'camera_detail.html', {'camera': camera})

def camera_ping(request, camera_name):
    """
    Realiza una simulación de ping a la cámara.
    """
    try:
        
        # Obtener la cámara por su nombre
        camera = Camera.objects.get(name=camera_name)
        
        # Verificar si el ping es válido (si no ha expirado)
        if camera.check_ping():
            return JsonResponse({'message': f'Camera {camera_name} is already pinged and active!'})
        
        # Si el ping no está activo, hacer el ping y actualizar el estado
        #camera.ping()  # Esto activará el ping y establecerá el tiempo
        mqtt_message = {
            "cam_target": camera_name,
        }
        send_message("ping_g15", json.dumps(mqtt_message))
        
        return JsonResponse({'message': f'Ping to camera {camera_name} please wait.'})

    except Camera.DoesNotExist:
        return JsonResponse({'error': f'Camera {camera_name} not found!'}, status=404)


