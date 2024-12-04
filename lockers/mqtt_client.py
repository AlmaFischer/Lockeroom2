import json
import os
import django
import paho.mqtt.client as mqtt
from django.conf import settings
from django.core.mail import EmailMessage
from django.shortcuts import get_object_or_404
import time
from django.utils import timezone


recent_messages = {}


# Configura Django para cargar las aplicaciones
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')  # Cambia 'your_project' al nombre de tu proyecto
django.setup()

from django.contrib.auth.models import User  # Importa el modelo User de Django
from lapp.models import Casillero, Camera, LockerLog  # Importa los modelos después de configurar Django

# Callback para manejar la conexión al broker
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to broker successfully")
        client.subscribe("open_locker_g15")  # Suscribirse al topic "open_locker"
        client.subscribe("new_camera_g15")  # Para agregar nuevos casilleros
        client.subscribe("close_locker_g15")  # Suscribirse al topic "close_locker"
        client.subscribe("pong_g15") #para recibir el pong del ESP32
        #client.subscribe("ping_g15")
    else:
        print("Failed to connect. Return code:", rc)

# Callback para manejar los mensajes recibidos
def on_message(client, userdata, msg):
    print(f"Received message: {msg.payload.decode()} on topic: {msg.topic}")
    
    if msg.topic == "open_locker_g15":
        try:
            # Parsear el mensaje JSON
            data = json.loads(msg.payload.decode())
            locker_id = data.get("id")
            camera_name = data.get("camera_name")

            if not locker_id or not camera_name:
                print("Missing locker_id or camera_name in the message.")
                return

            combined_locker_id = f"{camera_name}_{locker_id}"

            current_time = time.time()
            if combined_locker_id in recent_messages and current_time - recent_messages[combined_locker_id] < 5:
                print(f"Duplicate message ignored for locker ID {combined_locker_id}")
                return

            recent_messages[combined_locker_id] = current_time

            # Obtener el casillero
            casillero = get_object_or_404(Casillero, locker_id=combined_locker_id)
            usuario = casillero.usuario 

            # Crear un log de apertura
            LockerLog.objects.create(locker=casillero, event_type='open', user=usuario)

            # Enviar el correo al usuario notificando la apertura
            asunto = 'Notificación de apertura de casillero'
            mensaje = f"<p>Hola {usuario.username},</p><p>Tu casillero con ID {casillero.locker_id} de la cámara {camera_name} ha sido abierto.</p>"
            destinatarios = [usuario.email]

            email = EmailMessage(
                asunto,
                mensaje,
                settings.DEFAULT_FROM_EMAIL,
                destinatarios,
            )
            email.content_subtype = "html"
            email.send()

            print(f"Notification sent to {usuario.email} for locker ID {casillero.locker_id} in camera {camera_name}")

        except (json.JSONDecodeError, KeyError):
            print("Error processing message or invalid JSON format")

    elif msg.topic == "close_locker_g15":
        try:
            data = json.loads(msg.payload.decode())
            locker_id = data.get("id")
            camera_name = data.get("camera_name")

            if not locker_id or not camera_name:
                print("Missing locker_id or camera_name in the message.")
                return

            combined_locker_id = f"{camera_name}_{locker_id}"

            current_time = time.time()
            if combined_locker_id in recent_messages and current_time - recent_messages[combined_locker_id] < 5:
                print(f"Duplicate message ignored for locker ID {combined_locker_id}")
                return

            recent_messages[combined_locker_id] = current_time

            # Obtener el casillero
            casillero = get_object_or_404(Casillero, locker_id=combined_locker_id)
            usuario = casillero.usuario
            # Crear un log de cierre
            LockerLog.objects.create(locker=casillero, event_type='close', user=usuario)

            print(f"Locker {casillero.locker_id} closed")

        except (json.JSONDecodeError, KeyError):
            print("Error processing message or invalid JSON format")

    elif msg.topic == "new_camera_g15":
        print("Adding New Locker")
        try:
            # Parsear el mensaje JSON
            data = json.loads(msg.payload.decode())
            camera_name = data.get("camera_name")
            locker_count = data.get("locker_count", 0)

            if not camera_name or locker_count <= 0:
                print("Invalid data received for new locker")
                return

            # Verificar si la cámara ya existe
            camera = Camera.objects.filter(name=camera_name).first()

            if camera:
                print(f"Camera '{camera_name}' already exists in the database. No changes made.")
                return
            else:
                # Si la cámara no existe, se crea una nueva cámara
                camera = Camera.objects.create(name=camera_name)
                print(f"New camera '{camera_name}' added to the database.")

            # Agregar casilleros a la base de datos solo si la cámara es nueva o ya existe
            for i in range(camera.lockers_count, camera.lockers_count + locker_count):
                locker_id = f"{camera.name}_{i + 1}"
                Casillero.objects.create(
                    camera=camera,
                    locker_id=locker_id,
                    password="0000",  # Puedes establecer una contraseña por defecto o manejarla de otra manera
                )
                print(f"Locker '{locker_id}' added to camera '{camera_name}'.")

            # Actualizar la cantidad de casilleros en la cámara
            camera.lockers_count += locker_count
            camera.save()

        except json.JSONDecodeError:
            print("Error processing message or invalid JSON format")
    elif msg.topic == "pong_g15":
        print("Pong recived")
        try:
            data = json.loads(msg.payload.decode())
            camera_name = data.get("camera_name")
            status = data.get("status")
            print("HOLA")
            if status == "pong":
                print(f"Respuesta 'pong' recibida de la cámara: {camera_name}")
                camera = Camera.objects.get(name=camera_name)
                print(f"esta es la cam{camera.name}")
                camera.ping()
                # Aquí puedes realizar cualquier lógica adicional
                # Por ejemplo, guardar en la base de datos o notificar a la vista
                # guardar_pong_db(camera_name)

        except json.JSONDecodeError:
            print("Error processing message or invalid JSON format")

# Función para enviar mensajes al broker MQTT
def send_message(topic, message):
    result = client.publish(topic, message)
    status = result[0]
    if status == 0:
        print(f"Message '{message}' sent to topic '{topic}'")
    else:
        print(f"Failed to send message to topic {topic}")

# Configuración del cliente MQTT
client = mqtt.Client()
client.username_pw_set(settings.MQTT_USER, settings.MQTT_PASSWORD)
client.on_connect = on_connect
client.on_message = on_message

# Conexión al broker
client.connect(settings.MQTT_SERVER, settings.MQTT_PORT, settings.MQTT_KEEPALIVE)
client.loop_start()
