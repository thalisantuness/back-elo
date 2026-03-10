from django.db import models


class Regra(models.Model):
    TIPO_CHOICES = [
        ('por_compra', 'Por Compra'),
        ('por_valor', 'Por Valor'),
    ]

    regra_id = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=255)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    valor_minimo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pontos = models.IntegerField(default=0)
    multiplicador = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    ativa = models.BooleanField(default=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_update = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'regras'

    def __str__(self):
        return self.nome