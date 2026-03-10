from django.db import models
from .usuario import Usuario


class Recompensa(models.Model):
    recom_id = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='recompensas')
    nome = models.CharField(max_length=255)
    descricao = models.TextField(null=True, blank=True)
    imagem_url = models.TextField(null=True, blank=True)
    pontos = models.IntegerField(null=True, blank=True)
    estoque = models.IntegerField(null=True, blank=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_update = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'recompensas'

    def __str__(self):
        return self.nome