from django.db import models
from .usuario import Usuario

class Campanha(models.Model):
    campanha_id = models.AutoField(primary_key=True)
    empresa = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='campanhas')
    titulo = models.CharField(max_length=100)
    descricao = models.TextField(null=True, blank=True)
    imagem_url = models.TextField(null=True, blank=True)
    produtos = models.JSONField(default=list)
    recompensas = models.JSONField(default=list)
    data_inicio = models.DateTimeField()
    data_fim = models.DateTimeField()
    ativa = models.BooleanField(default=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_update = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'campanhas'
        indexes = [
            models.Index(fields=['empresa']),
            models.Index(fields=['ativa', 'data_inicio', 'data_fim']),
        ]

    def __str__(self):
        return self.titulo