from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.db.models import Q, Avg, Count
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import localtime
from .models import Producto, Trueque, Chat, Mensaje, Notificacion, Perfil, Moderacion, Calificacion
from .forms import MensajeForm
from datetime import timedelta
import json


# ---------------------- AUTH ----------------------
def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')
    return render(request, 'login.html')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email', '')
        password = request.POST.get('password')
        if User.objects.filter(username=username).exists():
            messages.error(request, 'El nombre de usuario ya existe.')
        else:
            User.objects.create_user(username=username, email=email, password=password)
            messages.success(request, 'Cuenta creada correctamente. Inicia sesión.')
            return redirect('login')
    return render(request, 'register.html')


def informacion(request):
    return render(request, "informacion.html")


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


# ---------------------- HOME ----------------------
@login_required
def home_view(request):
    user = request.user
    productos = Producto.objects.all().order_by('-fecha_agregado')

    notifs = Notificacion.objects.filter(usuario=user, visible=True).order_by('-creado')[:20]
    trueques_pendientes = Trueque.objects.filter(receptor=user, estado='pendiente').order_by('-fecha')
    trueques_aceptados = Trueque.objects.filter(estado='aceptado').filter(
        Q(solicitante=user) | Q(receptor=user)
    ).order_by('-fecha')

    # ------------------- RECOMENDACIONES -------------------
    if hasattr(user, "perfil") and user.perfil.intereses:
        intereses = [i.strip() for i in user.perfil.intereses.split(",") if i.strip()]
        recomendaciones = Producto.objects.filter(
            tags__nombre__in=intereses
        ).exclude(usuario=user).distinct()[:8]
        titulo_reco = "Recomendado según tus intereses"
    else:
        recomendaciones = Producto.objects.exclude(usuario=user).order_by('?')[:8]
        titulo_reco = "Quizás te interese"
    # -------------------------------------------------------

    # CREAR
    if request.method == 'POST' and request.POST.get('action') == 'crear_producto':
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion')
        imagen = request.FILES.get('imagen')
        if nombre and descripcion:
            Producto.objects.create(usuario=user, nombre=nombre, descripcion=descripcion, imagen=imagen)
            messages.success(request, 'Producto creado correctamente.')
        else:
            messages.error(request, 'Completa nombre y descripción.')
        return redirect('home')

    # EDITAR
    if request.method == 'POST' and request.POST.get('action') == 'editar_producto':
        producto_id = request.POST.get('producto_id')
        producto = get_object_or_404(Producto, id=producto_id)
        if producto.usuario != user:
            return HttpResponseForbidden("No tienes permiso para editar.")
        producto.nombre = request.POST.get('nombre')
        producto.descripcion = request.POST.get('descripcion')
        if 'imagen' in request.FILES:
            producto.imagen = request.FILES['imagen']
        producto.save()
        messages.success(request, 'Producto actualizado correctamente.')
        return redirect('home')

    # ELIMINAR
    if request.method == 'POST' and request.POST.get('action') == 'eliminar_producto':
        producto_id = request.POST.get('producto_id')
        producto = get_object_or_404(Producto, id=producto_id)
        if producto.usuario != user:
            return HttpResponseForbidden("No tienes permiso para eliminar.")
        producto.delete()
        messages.success(request, 'Producto eliminado correctamente.')
        return redirect('home')

    # OFRECER TRUEQUE
    if request.method == 'POST' and request.POST.get('action') == 'ofrecer_trueque':
        producto = get_object_or_404(Producto, id=request.POST.get('producto_id'))
        if producto.usuario == user:
            messages.error(request, 'No puedes ofrecer por tu propio producto.')
            return redirect('home')
        t = Trueque.objects.create(solicitante=user, receptor=producto.usuario, producto=producto)
        Notificacion.objects.create(
            usuario=producto.usuario,
            titulo='Nueva solicitud de trueque',
            mensaje=f'{user.username} ofreció un trueque por "{producto.nombre}".',
            tipo='nuevo_trueque',
            link=reverse('home')
        )
        messages.success(request, 'Solicitud de trueque enviada.')
        return redirect('home')

    # RESPONDER TRUEQUE
    if request.method == 'POST' and request.POST.get('action') == 'responder_trueque':
        trueque = get_object_or_404(Trueque, id=request.POST.get('trueque_id'))
        if trueque.receptor != user:
            return HttpResponseForbidden("No tienes permiso.")
        decision = request.POST.get('decision')
        if decision == 'aceptar':
            trueque.estado = 'aceptado'
            trueque.save()
            chat, created = Chat.objects.get_or_create(trueque=trueque)
            chat.usuarios.set([trueque.solicitante, trueque.receptor])
            chat_url = reverse('chat_detalle', args=[chat.id])

            Notificacion.objects.create(
                usuario=trueque.solicitante,
                titulo='Trueque aceptado',
                mensaje=f'{trueque.receptor.username} aceptó tu solicitud. Pulsa Ver chat.',
                tipo='trueque_aceptado',
                link=chat_url
            )
            Notificacion.objects.create(
                usuario=trueque.receptor,
                titulo='Trueque aceptado',
                mensaje=f'Aceptaste la solicitud de {trueque.solicitante.username}. Pulsa Ver chat.',
                tipo='trueque_aceptado',
                link=chat_url
            )
            messages.success(request, 'Trueque aceptado. Chat creado.')
        else:
            trueque.estado = 'rechazado'
            trueque.save()
            Notificacion.objects.create(
                usuario=trueque.solicitante,
                titulo='Trueque rechazado',
                mensaje=f'{trueque.receptor.username} rechazó tu solicitud por "{trueque.producto.nombre}".',
                tipo='trueque_rechazado',
                link=reverse('home')
            )
            messages.info(request, 'Trueque rechazado.')
        return redirect('home')

    context = {
        'productos': productos,
        'notificaciones': notifs,
        'trueques_pendientes': trueques_pendientes,
        'trueques_aceptados': trueques_aceptados,
        'chats': Chat.objects.filter(usuarios=user).order_by('-creado'),
        'recomendaciones': recomendaciones,
        'titulo_reco': titulo_reco,
    }

    return render(request, 'home.html', context)


# ---------------------- BUSQUEDA ----------------------
@login_required
def buscar_productos(request):
    texto = request.GET.get("q", "")
    productos = Producto.objects.filter(
        Q(nombre__icontains=texto) |
        Q(usuario__username__icontains=texto)
    ).order_by("-id")[:100]

    lista = []
    for p in productos:
        lista.append({
            "id": p.id,
            "nombre": p.nombre,
            "descripcion": p.descripcion[:120] + ("..." if len(p.descripcion) > 120 else ""),
            "usuario": p.usuario.username,
            "imagen": p.imagen.url if p.imagen else "/static/img/logo.png",
            "es_dueno": (request.user == p.usuario) or (request.user.username == "admin3000"),
        })

    return JsonResponse({"productos": lista})


# ---------------------- CRUD PRODUCTOS ----------------------
@login_required
def crear_producto(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion')
        imagen = request.FILES.get('imagen')
        if nombre and descripcion:
            Producto.objects.create(usuario=request.user, nombre=nombre, descripcion=descripcion, imagen=imagen)
            messages.success(request, 'Producto creado correctamente.')
    return redirect('home')


@login_required
def editar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    if producto.usuario != request.user:
        return HttpResponseForbidden("No autorizado")
    if request.method == 'POST':
        producto.nombre = request.POST.get('nombre')
        producto.descripcion = request.POST.get('descripcion')
        if 'imagen' in request.FILES:
            producto.imagen = request.FILES['imagen']
        producto.save()
        messages.success(request, 'Producto actualizado.')
    return redirect('home')


@login_required
def eliminar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    if producto.usuario != request.user:
        return HttpResponseForbidden("No autorizado")
    if request.method == 'POST':
        producto.delete()
        messages.success(request, 'Producto eliminado.')
    return redirect('home')


# ---------------------- TRUEQUES ----------------------
@login_required
def ofrecer_trueque(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    if producto.usuario == request.user:
        messages.error(request, 'No puedes ofrecer por tu propio producto.')
        return redirect('home')
    t = Trueque.objects.create(solicitante=request.user, receptor=producto.usuario, producto=producto)
    Notificacion.objects.create(
        usuario=producto.usuario,
        titulo='Nueva solicitud de trueque',
        mensaje=f'{request.user.username} ofreció un trueque por "{producto.nombre}".',
        tipo='nuevo_trueque',
        link=reverse('home')
    )
    messages.success(request, 'Solicitud de trueque enviada.')
    return redirect('home')


@login_required
def aceptar_trueque(request, trueque_id):
    trueque = get_object_or_404(Trueque, id=trueque_id)
    if trueque.receptor != request.user:
        return HttpResponseForbidden("No tienes permiso")
    trueque.estado = 'aceptado'
    trueque.save()
    chat, created = Chat.objects.get_or_create(trueque=trueque)
    chat.usuarios.set([trueque.solicitante, trueque.receptor])
    chat_url = reverse('chat_detalle', args=[chat.id])
    Notificacion.objects.create(
        usuario=trueque.solicitante,
        titulo='Trueque aceptado',
        mensaje=f'{trueque.receptor.username} aceptó tu solicitud. Pulsa Ver chat.',
        tipo='trueque_aceptado',
        link=chat_url
    )
    Notificacion.objects.create(
        usuario=trueque.receptor,
        titulo='Trueque aceptado',
        mensaje=f'Aceptaste la solicitud de {trueque.solicitante.username}. Pulsa Ver chat.',
        tipo='trueque_aceptado',
        link=chat_url
    )
    messages.success(request, 'Trueque aceptado.')
    return redirect('home')


@login_required
def rechazar_trueque(request, trueque_id):
    trueque = get_object_or_404(Trueque, id=trueque_id)
    if trueque.receptor != request.user:
        return HttpResponseForbidden("No tienes permiso")
    trueque.estado = 'rechazado'
    trueque.save()
    Notificacion.objects.create(
        usuario=trueque.solicitante,
        titulo='Trueque rechazado',
        mensaje=f'{trueque.receptor.username} rechazó tu solicitud por "{trueque.producto.nombre}".',
        tipo='trueque_rechazado',
        link=reverse('home')
    )
    messages.info(request, 'Trueque rechazado.')
    return redirect('home')


# ---------------------- CHAT ----------------------
@login_required
def chat_list_view(request):
    chats = Chat.objects.filter(usuarios=request.user).order_by('-creado')
    return render(request, 'chat.html', {'chats': chats, 'user': request.user})


@login_required
def chat_detalle(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id)
    if request.user not in chat.usuarios.all():
        return HttpResponseForbidden("No tienes acceso a este chat.")
    mensajes = chat.mensajes.all().order_by('fecha')
    form = MensajeForm()
    return render(request, 'chat.html', {
        'chat': chat,
        'mensajes': mensajes,
        'form': form,
        'chats': Chat.objects.filter(usuarios=request.user).order_by('-creado'),
        'chat_seleccionado': chat
    })


@login_required
@csrf_exempt
def api_send_message(request, chat_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'error': 'Formato JSON inválido'}, status=400)
        texto = data.get('texto', '').strip()
        if not texto:
            return JsonResponse({'ok': False, 'error': 'Mensaje vacío'}, status=400)
        chat = get_object_or_404(Chat, id=chat_id)
        if request.user not in chat.usuarios.all():
            return JsonResponse({'ok': False, 'error': 'No autorizado'}, status=403)
        mensaje = Mensaje.objects.create(chat=chat, autor=request.user, contenido=texto)
        
        otros = [u for u in chat.usuarios.all() if u != request.user]
        if otros:
            Notificacion.objects.create(
                usuario=otros[0],
                titulo='Nuevo mensaje',
                mensaje=f'{request.user.username} te envió un mensaje.',
                tipo='mensaje',
                link=reverse('chat_detalle', args=[chat.id])
            )
        return JsonResponse({
            'ok': True,
            'mensaje': {
                'id': mensaje.id,
                'autor': mensaje.autor.username,
                'contenido': mensaje.contenido,
                'fecha': localtime(mensaje.fecha).strftime('%d/%m/%Y %H:%M')
            }
        })
    return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)


@login_required
def api_fetch_messages(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id)
    if request.user not in chat.usuarios.all():
        return JsonResponse({'error': 'No autorizado'}, status=403)

    since_id = request.GET.get('since_id')
    if since_id:
        try:
            since_id = int(since_id)
        except (ValueError, TypeError):
            since_id = None

    if since_id:
        msgs = chat.mensajes.filter(id__gt=since_id).order_by('fecha')
    else:
        msgs = chat.mensajes.all().order_by('fecha')

    datos = [{
        'id': m.id,
        'autor': m.autor.username,
        'contenido': m.contenido,
        'fecha': m.fecha.strftime("%d/%m/%Y %H:%M")
    } for m in msgs]
    return JsonResponse({'mensajes': datos})


# ---------------------- NOTIFICACIONES ----------------------
@login_required
def api_notificaciones(request):
    user = request.user
    notifs = Notificacion.objects.filter(usuario=user, visible=True).order_by('-creado')[:20]
    ahora = timezone.now()
    datos = []
    for n in notifs:
        edad = (ahora - n.creado).total_seconds()
        datos.append({
            'id': n.id,
            'titulo': n.titulo,
            'mensaje': n.mensaje,
            'tipo': n.tipo,
            'link': n.link,
            'creado_iso': n.creado.isoformat(),
            'edad_segundos': int(edad),
        })
    return JsonResponse({'notificaciones': datos})


@login_required
@require_POST
def api_marcar_leida(request):
    nid = request.POST.get('id')
    try:
        n = Notificacion.objects.get(id=nid, usuario=request.user)
        n.visible = False
        n.save()
        return JsonResponse({'ok': True})
    except Notificacion.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'No encontrada'}, status=404)


# ---------------------- REPORTAR & CALIFICAR ----------------------
@login_required
@require_POST
def reportar_chat(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id)
    if request.user not in chat.usuarios.all():
        return JsonResponse({'ok': False, 'error': 'No autorizado'}, status=403)

    mensaje_texto = (
        "El equipo de soporte de Swap Place estará revisando su conversación "
        "en busca de la razón del reporte. Gracias por avisar. "
        "Recibirá la noticia de este caso en las próximas 72 hrs. "
        "Gracias por preferir SwapPlace."
    )
    return JsonResponse({'ok': True, 'mensaje': mensaje_texto})

# Calificacion
@login_required
@csrf_exempt
def calificar_chat(request, chat_id):
    """
    Permite que un usuario califique a otro usuario en un chat.
    """
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Método no permitido"}, status=405)

    try:
        data = json.loads(request.body)
        estrellas = int(data.get("estrellas", 0))
        if estrellas < 1 or estrellas > 5:
            return JsonResponse({"ok": False, "error": "Valor de estrellas inválido"}, status=400)
        
        chat = Chat.objects.get(id=chat_id)
        if request.user not in chat.usuarios.all():
            return JsonResponse({"ok": False, "error": "No autorizado"}, status=403)

        # El vendedor es quien no es el usuario que califica
        vendedor = next(u for u in chat.usuarios.all() if u != request.user)

        # Crear o actualizar calificación
        calificacion, created = Calificacion.objects.update_or_create(
            vendedor=vendedor,
            comprador=request.user,
            trueque=chat.trueque,
            defaults={"estrellas": estrellas}
        )

        # Actualizar perfil del vendedor
        perfil_vendedor, _ = Perfil.objects.get_or_create(usuario=vendedor)
        perfil_vendedor.agregar_calificacion(estrellas)

        return JsonResponse({"ok": True, "estrellas": estrellas})

    except Chat.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Chat no encontrado"}, status=404)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)

# ---------------------- PANEL DEL VENDEDOR ----------------------
@login_required
def panel_vendedor(request):
    perfil, _ = Perfil.objects.get_or_create(usuario=request.user)

    productos = Producto.objects.filter(usuario=request.user)
    total_productos = productos.count()
    total_visitas = sum(p.visitas for p in productos)
    promedio_estrellas = perfil.promedio_estrellas()

    # NUEVO: Contar trueques recibidos
    total_trueques_recibidos = Trueque.objects.filter(
        receptor=request.user
    ).count()

    return render(request, 'panel_vendedor.html', {
        'perfil': perfil,
        'productos': productos,
        'total_productos_vendedor': total_productos,
        'total_visitas': total_visitas,
        'promedio_estrellas': promedio_estrellas,
        'total_trueques_recibidos': total_trueques_recibidos,
    })

# ---------------------- INSIGHTS ADMIN ----------------------
@login_required
def panel_insight(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Acceso denegado.")

    producto_mas_solicitado = (
        Trueque.objects.values("producto__nombre")
        .annotate(total=Count("id"))
        .order_by("-total")
        .first()
    )

    total_trueques = Trueque.objects.count()
    total_usuarios = User.objects.count()
    total_productos = Producto.objects.count()

    return render(request, "panel_insights.html", {
        "producto_mas_solicitado": producto_mas_solicitado,
        "total_trueques": total_trueques,
        "total_usuarios": total_usuarios,
        "total_productos": total_productos,
    })

# ---------------------- MODERAR USUARIOS ----------------------
@login_required
def moderar_usuario(request):
    if not request.user.is_superuser or request.user.username != "admin3000":
        return HttpResponseForbidden("Acceso denegado.")

    if request.method == "POST":
        usuario_id = request.POST.get("usuario_id")
        accion = request.POST.get("accion")

        usuario = get_object_or_404(User, id=usuario_id)

        # Asegurar que el usuario tenga Perfil
        perfil, creado = Perfil.objects.get_or_create(usuario=usuario)

        if accion == "bloquear":
            # 1. Bloquear usuario
            moderacion, created = Moderacion.objects.get_or_create(usuario=usuario)
            moderacion.estado = "bloqueado"
            moderacion.save()

            # 2. Registrar strike
            perfil.advertencias += 1
            perfil.save()

            # 3. Notificación al usuario
            Notificacion.objects.create(
                usuario=usuario,
                titulo="Has recibido un strike",
                mensaje=f"Tu cuenta ha recibido un strike. Strike {perfil.advertencias}/3.",
                tipo="alerta"
            )

            # 4. Si llega a 3 strikes → eliminar usuario
            if perfil.advertencias >= 3:
                Notificacion.objects.create(
                    usuario=usuario,
                    titulo="Cuenta eliminada",
                    mensaje="Tu cuenta ha sido eliminada por acumular 3 strikes.",
                    tipo="peligro"
                )

                # Eliminar contenido asociado
                Producto.objects.filter(usuario=usuario).delete()
                Trueque.objects.filter(solicitante=usuario).delete()
                Trueque.objects.filter(receptor=usuario).delete()
                Chat.objects.filter(usuarios=usuario).delete()

                usuario.delete()

                return redirect('moderar_usuario')

        elif accion == "desbloquear":
            Moderacion.objects.filter(usuario=usuario).update(estado="activo")

            Notificacion.objects.create(
                usuario=usuario,
                titulo="Tu cuenta ha sido desbloqueada",
                mensaje="Un administrador ha restaurado el acceso a tu cuenta.",
                tipo="info"
            )

    usuarios = User.objects.all()
    moderados = Moderacion.objects.all()

    return render(request, "moderar_usuarios.html", {
        "usuarios": usuarios,
        "moderados": moderados,
    })

@login_required
def api_strikes(request):
    """
    Devuelve las notificaciones de strike NO leídas.
    """
    notifs = Notificacion.objects.filter(
        usuario=request.user,
        visible=True,
        tipo__in=["alerta", "peligro"]   # Las que son strikes
    ).order_by('-creado')

    data = [{
        "id": n.id,
        "titulo": n.titulo,
        "mensaje": n.mensaje,
        "fecha": n.creado.isoformat(),
    } for n in notifs]

    return JsonResponse({"strikes": data})