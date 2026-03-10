from django.db import transaction


class BaseRepository:
    """Repositório base com operações comuns"""

    def __init__(self, model_class):
        self.model_class = model_class

    def get_by_id(self, id):
        """Busca por ID"""
        try:
            return self.model_class.objects.get(pk=id)
        except self.model_class.DoesNotExist:
            return None

    def get_all(self, filters=None):
        """Lista todos com filtros opcionais"""
        queryset = self.model_class.objects.all()
        if filters:
            queryset = queryset.filter(**filters)
        return queryset

    def create(self, **kwargs):
        """Cria novo registro"""
        return self.model_class.objects.create(**kwargs)

    def update(self, instance, **kwargs):
        """Atualiza registro"""
        for key, value in kwargs.items():
            setattr(instance, key, value)
        instance.save()
        return instance

    def delete(self, instance):
        """Deleta registro"""
        instance.delete()

    @transaction.atomic
    def transaction_create(self, **kwargs):
        """Cria em transação"""
        return self.create(**kwargs)