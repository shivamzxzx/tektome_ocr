from ninja.security import HttpBearer
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth.models import User


class JWTAuth(HttpBearer):
    def authenticate(self, request, token):
        try:
            # Decode the JWT token
            access_token = AccessToken(token)
            # Get the user from the token
            user = User.objects.get(id=access_token["user_id"])
            return user
        except Exception as e:
            # If token is invalid or expired
            return None
