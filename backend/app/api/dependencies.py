from app.services.session_service import SessionService

session_service = SessionService()


def get_session_service() -> SessionService:
    return session_service
