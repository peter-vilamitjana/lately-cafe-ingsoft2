from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailOUsernameBackend(ModelBackend):
    """Permite iniciar sesión con email o con nombre de usuario."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD) or kwargs.get("email")
        if not username or not password:
            return None

        # Priorizamos búsqueda por email exacto (insensible a mayúsculas) y luego por username
        user = UserModel.objects.filter(email__iexact=username).first()
        if not user:
            user = UserModel.objects.filter(username__iexact=username).first()

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
