from ninja.security import HttpBearer
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth.models import User


class JWTAuth(HttpBearer):
    """
        Custom authentication class for JWT-based authentication.
        Verifies and decodes the JWT token from the request header to authenticate the user.
    """
    def authenticate(self, request, token):
        """
                Authenticates the user by decoding the JWT token.

                :param request: The HTTP request object.
                :param token: The JWT token from the Authorization header.
                :return: The authenticated user if the token is valid, otherwise None.
        """
        try:
            # Decode the JWT token
            access_token = AccessToken(token)
            # Get the user from the token
            user = User.objects.get(id=access_token["user_id"])
            return user
        except Exception as e:
            # If token is invalid or expired
            return None
