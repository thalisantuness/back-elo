from django.db import models
from .compra import Compra
from .usuario import Usuario


class QRCode(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('escaneado', 'Escaneado'),
        ('validado', 'Validado'),
        ('expirado', 'Expirado'),
    ]

    qr_code_id = models.CharField(max_length=100, primary_key=True)
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name='qrcodes')
    empresa = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='qrcodes_empresa')
    cliente = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='qrcodes_cliente')
    qr_data = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pendente')
    escaneado_em = models.DateTimeField(null=True, blank=True)
    expira_em = models.DateTimeField()
    data_cadastro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'qrcodes'

    def __str__(self):
        return self.qr_code_id