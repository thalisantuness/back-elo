from django.db import models
from .usuario import Usuario
from .campanha import Campanha


class Compra(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('validada', 'Validada'),
        ('cancelada', 'Cancelada'),
        ('expirada', 'Expirada'),
    ]

    compra_id = models.AutoField(primary_key=True)
    qr_code_id = models.CharField(max_length=100, unique=True)
    cliente = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='compras_cliente')
    empresa = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='compras_empresa')
    campanha = models.ForeignKey(Campanha, on_delete=models.SET_NULL, null=True, blank=True)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    pontos_adquiridos = models.IntegerField(default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pendente')
    qr_code_data = models.TextField()
    qr_code_expira_em = models.DateTimeField()
    validado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='validacoes')
    validado_em = models.DateTimeField(null=True, blank=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_update = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'compras'
        indexes = [
            models.Index(fields=['qr_code_id']),
            models.Index(fields=['status']),
            models.Index(fields=['empresa', 'status']),
            models.Index(fields=['cliente', 'status']),
        ]

    def __str__(self):
        return f"Compra {self.compra_id} - {self.valor}"