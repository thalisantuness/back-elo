from django.db import models
from .usuario import Usuario


class Produto(models.Model):
    produto_id = models.AutoField(primary_key=True)
    empresa = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='produtos')
    nome = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    valor_custo = models.DecimalField(max_digits=10, decimal_places=2)
    quantidade = models.IntegerField()
    tipo_comercializacao = models.CharField(max_length=100)
    tipo_produto = models.CharField(max_length=100)
    empresas_autorizadas = models.JSONField(default=list, null=True, blank=True)
    foto_principal = models.TextField(null=True, blank=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_update = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'produtos'

    def __str__(self):
        return self.nome


class Foto(models.Model):
    photo_id = models.AutoField(primary_key=True)
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='fotos')
    imageData = models.TextField()
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_update = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'produto_foto'