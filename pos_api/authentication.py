import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import User

class CookieJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        # Extract token from the cookies
        token = request.COOKIES.get('accessToken')
        if not token:
            return None
        
        try:
            # Decode the token using the settings.SECRET_KEY
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token has expired!')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Invalid Token!')
            
        user_id = payload.get('_id')
        if not user_id:
            raise AuthenticationFailed('Invalid Token payload!')
            
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise AuthenticationFailed('User not exist!')
            
        return (user, token)
