from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# ======================================================
# PERFIL (calificaciones, moderación, intereses, favoritos)
# ======================================================
class Perfil(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name="perfil")

    # --- Calificaciones ---
    estrellas_totales = models.PositiveIntegerField(default=0)
    cantidad_calificaciones = models.PositiveIntegerField(default=0)

    # --- Moderación ---
    suspendido = models.BooleanField(default=False)
    razon_suspension = models.CharField(max_length=300, blank=True)
    fecha_suspension = models.DateTimeField(null=True, blank=True)
    advertencias = models.PositiveIntegerField(default=0)

    # --- Personalización / Recomendaciones ---
    intereses = models.CharField(
        max_length=300,
        blank=True,
        help_text="Intereses separados por comas. Ej: tecnología,ropa,hogar"
    )

    # --- Favoritos (wishlist) ---
    favoritos = models.ManyToManyField('Producto', blank=True, related_name='favoritos_de')

    def agregar_calificacion(self, estrellas: int):
        self.estrellas_totales += estrellas
        self.cantidad_calificaciones += 1
        self.save()

    def promedio_estrellas(self):
        if self.cantidad_calificaciones == 0:
            return 0
        return round(self.estrellas_totales / self.cantidad_calificaciones, 2)

    def __str__(self):
        return f"Perfil de {self.usuario.username}"


# ======================================================
# CATEGORÍAS
# ======================================================
class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre


# ======================================================
# TAGS para recomendaciones
# ======================================================
class Tag(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre


# ======================================================
# PRODUCTO
# ======================================================
class Producto(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True)
    fecha_agregado = models.DateTimeField(auto_now_add=True)

    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True)

    visitas = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.nombre


# ======================================================
# TRUEQUE
# ======================================================
class Trueque(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('aceptado', 'Aceptado'),
        ('rechazado', 'Rechazado'),
    ]

    solicitante = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trueques_solicitados')
    receptor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trueques_recibidos')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    estado = models.CharField(max_length=10, choices=ESTADOS, default='pendiente')
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.solicitante.username} → {self.receptor.username} ({self.estado})"


# ======================================================
# CHAT
# ======================================================
class Chat(models.Model):
    trueque = models.OneToOneField(Trueque, on_delete=models.CASCADE, related_name='chat')
    usuarios = models.ManyToManyField(User)
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        try:
            nombres = ', '.join([u.username for u in self.usuarios.all()])
        except:
            nombres = "Chat"
        return f"Chat entre {nombres}"


# ======================================================
# MENSAJE
# ======================================================
class Mensaje(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='mensajes')
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    contenido = models.TextField(max_length=500)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.autor.username}: {self.contenido[:30]}"


# ======================================================
# NOTIFICACIONES
# ======================================================
class Notificacion(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificaciones')
    titulo = models.CharField(max_length=150)
    mensaje = models.CharField(max_length=300)
    tipo = models.CharField(max_length=50, blank=True)
    link = models.CharField(max_length=300, blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    visible = models.BooleanField(default=True)

    def __str__(self):
        return f"Notif a {self.usuario.username}: {self.titulo}"


# ======================================================
# REPORTES
# ======================================================
class Reporte(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    reportante = models.ForeignKey(User, on_delete=models.CASCADE)
    motivo = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reporte de {self.reportante.username} en chat {self.chat.id}"


# ======================================================
# CALIFICACIONES
# ======================================================
class Calificacion(models.Model):
    vendedor = models.ForeignKey(User, related_name='calificaciones_recibidas', on_delete=models.CASCADE)
    comprador = models.ForeignKey(User, related_name='calificaciones_realizadas', on_delete=models.CASCADE)
    trueque = models.ForeignKey(Trueque, on_delete=models.CASCADE)
    estrellas = models.IntegerField(default=1)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('vendedor', 'comprador', 'trueque')

    def __str__(self):
        return f"{self.comprador.username} → {self.vendedor.username} ({self.estrellas}⭐)"


# ======================================================
# MODERACIÓN
# ======================================================
class Moderacion(models.Model):
    ESTADOS = (
        ('bloqueado', 'Bloqueado'),
        ('activo', 'Activo'),
    )

    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='activo')
    fecha_modificacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.usuario.username} - {self.estado}"
