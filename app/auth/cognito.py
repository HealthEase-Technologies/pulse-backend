import boto3
import jwt
import requests
from typing import Dict, Optional
from app.config.settings import settings
from fastapi import HTTPException, status

class CognitoAuth:
    def __init__(self):
        self.region = settings.aws_region
        self.user_pool_id = settings.cognito_user_pool_id
        self.client_id = settings.cognito_client_id
        self.jwks_url = f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}/.well-known/jwks.json"
        self._jwks = None

    def get_jwks(self):
        """Get JSON Web Key Set from Cognito"""
        if not self._jwks:
            response = requests.get(self.jwks_url)
            self._jwks = response.json()
        return self._jwks

    async def verify_token(self, token: str) -> Dict:
        """Verify JWT token from Cognito"""
        try:
            # Decode header to get kid
            header = jwt.get_unverified_header(token)
            kid = header['kid']
            
            # Get the public key
            jwks = self.get_jwks()
            key = None
            for k in jwks['keys']:
                if k['kid'] == kid:
                    key = jwt.algorithms.RSAAlgorithm.from_jwk(k)
                    break
            
            if not key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unable to find appropriate key"
                )
            
            # Verify and decode token
            decoded_token = jwt.decode(
                token,
                key,
                algorithms=['RS256'],
                audience=self.client_id,
                issuer=f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}"
            )
            
            return decoded_token
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )

cognito_auth = CognitoAuth()