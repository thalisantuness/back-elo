from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication


class BaseView:
    """Classe base para views com métodos utilitários"""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_user(self, request):
        """Retorna o usuário autenticado"""
        return request.user

    def get_user_role(self, request):
        """Retorna a role do usuário"""
        return getattr(request.user, 'role', None)

    def success_response(self, data=None, message=None, status_code=status.HTTP_200_OK):
        """Resposta de sucesso padronizada"""
        response = {'success': True}
        if message:
            response['message'] = message
        if data is not None:
            response['data'] = data
        return Response(response, status=status_code)

    def error_response(self, message, status_code=status.HTTP_400_BAD_REQUEST, errors=None):
        """Resposta de erro padronizada"""
        response = {
            'success': False,
            'error': message
        }
        if errors:
            response['errors'] = errors
        return Response(response, status=status_code)

    def not_found_response(self, message="Recurso não encontrado"):
        """Resposta de não encontrado"""
        return self.error_response(message, status.HTTP_404_NOT_FOUND)

    def forbidden_response(self, message="Acesso negado"):
        """Resposta de acesso negado"""
        return self.error_response(message, status.HTTP_403_FORBIDDEN)