from functools import lru_cache
from pathlib import Path
from typing import Any

import firebase_admin
from firebase_admin import auth, credentials
from firebase_admin.exceptions import FirebaseError

from app.config.settings import settings


class InvalidFirebaseToken(Exception):
    pass


@lru_cache(maxsize=1)
def get_firebase_app() -> firebase_admin.App:
    try:
        return firebase_admin.get_app()
    except ValueError:
        if settings.firebase_credentials_path:
            credentials_path = Path(settings.firebase_credentials_path)
            if not credentials_path.is_file():
                raise RuntimeError(
                    "Firebase Admin credentials file was not found at FIREBASE_CREDENTIALS_PATH"
                )
            credential = credentials.Certificate(str(credentials_path))
        else:
            credential = credentials.ApplicationDefault()
        return firebase_admin.initialize_app(
            credential,
            {"projectId": settings.firebase_project_id},
        )


def verify_firebase_id_token(id_token: str) -> dict[str, Any]:
    try:
        return auth.verify_id_token(id_token, app=get_firebase_app(), check_revoked=True)
    except (FirebaseError, ValueError) as error:
        raise InvalidFirebaseToken("Firebase ID token is invalid or expired") from error
