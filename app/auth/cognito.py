import boto3
import jwt
import requests
import logging
from datetime import timedelta
from typing import Dict, Optional
from app.config.settings import settings
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

class CognitoAuth:
    def __init__(self):
        self.region = settings.aws_region
        self.user_pool_id = settings.cognito_user_pool_id
        self.client_id = settings.cognito_client_id
        self.jwks_url = f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}/.well-known/jwks.json"
        self._jwks = None
        self.cognito_client = boto3.client('cognito-idp', region_name=self.region)

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

            # Refresh JWKS if the kid is not found (keys may have rotated)
            jwks = self.get_jwks()
            key = None
            for k in jwks['keys']:
                if k['kid'] == kid:
                    key = jwt.algorithms.RSAAlgorithm.from_jwk(k)
                    break

            if not key:
                # Force refresh JWKS cache and retry once
                self._jwks = None
                jwks = self.get_jwks()
                for k in jwks['keys']:
                    if k['kid'] == kid:
                        key = jwt.algorithms.RSAAlgorithm.from_jwk(k)
                        break

            if not key:
                logger.error(f"No matching key for kid={kid}. Available kids: {[k['kid'] for k in jwks['keys']]}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unable to find appropriate key"
                )

            # Verify and decode token (30s leeway for clock skew)
            decoded_token = jwt.decode(
                token,
                key,
                algorithms=['RS256'],
                audience=self.client_id,
                issuer=f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}",
                leeway=timedelta(seconds=30),
            )

            return decoded_token

        except jwt.ExpiredSignatureError:
            logger.warning("Token rejected: expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidAudienceError as e:
            logger.error(f"Token rejected: audience mismatch — expected={self.client_id}, error={e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token audience: {str(e)}"
            )
        except jwt.InvalidIssuerError as e:
            logger.error(f"Token rejected: issuer mismatch — {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token issuer: {str(e)}"
            )
        except jwt.InvalidTokenError as e:
            logger.error(f"Token rejected: {type(e).__name__} — {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )

    # Delete user method disabled - not in use due to AWS credential issues
    # async def delete_user(self, username: str) -> Dict:
    #     """
    #     Delete a user from Cognito by username (email)
    #
    #     First disables the user, then deletes them to ensure clean removal.
    #
    #     Args:
    #         username: The username (email) of the user to delete
    #
    #     Returns:
    #         dict: Status of deletion with details
    #
    #     Raises:
    #         Exception: If deletion fails (with detailed error message)
    #     """
    #     try:
    #         # Step 1: Disable the user first (AWS best practice)
    #         try:
    #             self.cognito_client.admin_disable_user(
    #                 UserPoolId=self.user_pool_id,
    #                 Username=username
    #             )
    #             print(f"Successfully disabled Cognito user: {username}")
    #         except self.cognito_client.exceptions.UserNotFoundException:
    #             print(f"User {username} not found in Cognito - already deleted")
    #             return {"success": True, "message": "User already deleted from Cognito"}
    #         except Exception as disable_error:
    #             print(f"Warning: Failed to disable user (continuing with delete): {str(disable_error)}")
    #
    #         # Step 2: Delete the user
    #         self.cognito_client.admin_delete_user(
    #             UserPoolId=self.user_pool_id,
    #             Username=username
    #         )
    #         print(f"Successfully deleted Cognito user: {username}")
    #         return {"success": True, "message": "User deleted from Cognito"}
    #
    #     except self.cognito_client.exceptions.UserNotFoundException:
    #         # User already deleted from Cognito, that's fine
    #         print(f"User {username} not found in Cognito - already deleted")
    #         return {"success": True, "message": "User already deleted from Cognito"}
    #     except Exception as e:
    #         error_msg = f"Failed to delete user from Cognito: {str(e)}"
    #         print(f"ERROR: {error_msg}")
    #         raise Exception(error_msg)

cognito_auth = CognitoAuth()