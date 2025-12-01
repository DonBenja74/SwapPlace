from django.urls import path
from . import views

urlpatterns = [
    # HOME
    path('', views.home_view, name='home'),

    # AUTENTICACIÓN
    path('login/', views.login_view, name='login'),
    path('registro/', views.register_view, name='registro'),
    path('logout/', views.logout_view, name='logout'),
    path('informacion/', views.informacion, name='informacion'),

    # PRODUCTOS
    path('crear-producto/', views.crear_producto, name='crear_producto'),
    path('editar-producto/<int:producto_id>/', views.editar_producto, name='editar_producto'),
    path('eliminar-producto/<int:producto_id>/', views.eliminar_producto, name='eliminar_producto'),
    path("buscar-productos/", views.buscar_productos, name="buscar_productos"),

    # TRUEQUES
    path('ofrecer-trueque/<int:producto_id>/', views.ofrecer_trueque, name='ofrecer_trueque'),
    path('aceptar-trueque/<int:trueque_id>/', views.aceptar_trueque, name='aceptar_trueque'),
    path('rechazar-trueque/<int:trueque_id>/', views.rechazar_trueque, name='rechazar_trueque'),

    # CHAT
    path('chats/', views.chat_list_view, name='chat_list'),
    path('chat/<int:chat_id>/', views.chat_detalle, name='chat_detalle'),
    path('api/chat/<int:chat_id>/send/', views.api_send_message, name='api_send_message'),
    path('api/chat/<int:chat_id>/messages/', views.api_fetch_messages, name='api_fetch_messages'),

    # NOTIFICACIONES API
    path('api/notificaciones/', views.api_notificaciones, name='api_notificaciones'),
    path('api/notificaciones/marcar/', views.api_marcar_leida, name='api_marcar_leida'),
    path("api/strikes/", views.api_strikes, name="api_strikes"),

    # PANELES
    path('panel/vendedor/', views.panel_vendedor, name='panel_vendedor'),
    path('panel/insight/', views.panel_insight, name='panel_insight'),

    # MODERAR USUARIOS
    path('moderar-usuarios/', views.moderar_usuario, name='moderar_usuario'),

    # ACCIONES DE CHAT
    path('chat/<int:chat_id>/reportar/', views.reportar_chat, name='reportar_chat'),
    path('chat/<int:chat_id>/calificar/', views.calificar_chat, name='calificar_chat'),
    path('chat/<int:chat_id>/calificar/', views.calificar_chat, name='api_calificar_vendedor'),

]
