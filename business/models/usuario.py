import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


class UsuarioManager(BaseUserManager):
    def create_user(self, email, nome, password=None, **extra_fields):
        if not email:
            raise ValueError('O email é obrigatório')
        email = self.normalize_email(email)
        user = self.model(email=email, nome=nome, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, nome, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('status', 'ativo')
        return self.create_user(email, nome, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('admin', 'Administrador'),
        ('cdl', 'CDL'),
        ('empresa', 'Empresa'),
        ('cliente', 'Cliente'),
        ('empresa-funcionario', 'Funcionário de Empresa'),
    ]

    STATUS_CHOICES = [
        ('ativo', 'Ativo'),
        ('pendente', 'Pendente'),
        ('bloqueado', 'Bloqueado'),
    ]

    MODALIDADE_PONTUACAO_CHOICES = [
        ('regras', 'Regras'),
        ('1pt_real_1pt_compra', '1 ponto por real'),
    ]

    usuario_id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    # Relacionamento com CDL (auto-relacionamento)
    cdl = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='membros')

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    nome = models.CharField(max_length=255)
    telefone = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(unique=True)
    foto_perfil = models.TextField(null=True, blank=True)

    # Cliente fields
    cliente_endereco = models.TextField(null=True, blank=True)
    cidade = models.CharField(max_length=100, null=True, blank=True)
    estado = models.CharField(max_length=2, null=True, blank=True)
    pontos = models.IntegerField(default=0)

    # Empresa fields
    cnpj = models.CharField(max_length=18, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pendente')

    # Relação com Regra
    regra = models.ForeignKey('Regra', on_delete=models.SET_NULL, null=True, blank=True, related_name='usuarios')

    modalidade_pontuacao = models.CharField(
        max_length=50,
        choices=MODALIDADE_PONTUACAO_CHOICES,
        default='regras'
    )

    # Timestamps
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    # Django auth fields
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    # 👇 ADICIONE ESTAS DUAS LINHAS PARA RESOLVER O CONFLITO
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='business_usuario_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='business_usuario_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    objects = UsuarioManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nome', 'role']

    class Meta:
        db_table = 'usuarios'
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['cdl']),
            models.Index(fields=['cidade', 'estado']),
        ]

    def __str__(self):
        return f"{self.nome} ({self.email})"