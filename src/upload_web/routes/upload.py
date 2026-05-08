from __future__ import annotations

from typing import Annotated, Any
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse

from src.shared.auth.entra import AuthenticatedUser
from src.upload_web.middleware import get_upload_current_user
from src.upload_web.services.upload_session import create_upload_session, get_all_user_sessions

router = APIRouter(tags=["upload-web"])
CurrentUser = Annotated[AuthenticatedUser, Depends(get_upload_current_user)]
POST_LOGIN_REDIRECT_PATH = "/dashboard"
STATUS_FILTERS = ["created", "uploading", "preflight", "confirmed", "processing", "completed", "failed"]
STATUS_BADGES = {
    "created": ("Creado", "bg-slate-100 text-slate-600"),
    "uploading": ("Subiendo", "bg-sky-100 text-sky-700"),
    "preflight": ("Preflight", "bg-violet-100 text-violet-700"),
    "confirmed": ("Confirmado", "bg-amber-100 text-amber-700"),
    "processing": ("Procesando", "bg-yellow-100 text-yellow-700"),
    "completed": ("Completado", "bg-green-100 text-green-700"),
    "failed": ("Error", "bg-red-100 text-red-700"),
}


def _build_template_context(
    request: Request,
    current_user: AuthenticatedUser,
    **extra: Any,
) -> dict[str, Any]:
    flash_messages = getattr(request.state, "flash_messages", [])
    context: dict[str, Any] = {
        "request": request,
        "current_user": current_user,
        "flash_messages": flash_messages,
    }
    context.update(extra)
    return context


def _microsoft_login_url(request: Request) -> str:
    post_login_redirect_uri = request.app.state.settings.build_public_url(POST_LOGIN_REDIRECT_PATH)
    return f"/.auth/login/aad?{urlencode({'post_login_redirect_uri': post_login_redirect_uri})}"


def _build_upload_rows(sessions: list[Any], status_filter: str = "") -> list[dict[str, Any]]:
    uploads: list[dict[str, Any]] = []
    for session in sessions:
        if status_filter and session.status != status_filter:
            continue
        status_label, status_classes = STATUS_BADGES.get(
            session.status, (session.status.capitalize(), "bg-slate-100 text-slate-600")
        )
        preflight = session.preflight
        for upload_file in session.files:
            uploads.append(
                {
                    "session_id": session.session_id,
                    "filename": upload_file.filename,
                    "status": session.status,
                    "status_label": status_label,
                    "status_classes": status_classes,
                    "albaran_group": upload_file.albaran_group,
                    "uploaded_at": upload_file.uploaded_at.strftime("%d/%m/%Y %H:%M"),
                    "uploaded_at_sort": upload_file.uploaded_at,
                    "content_type": upload_file.content_type,
                    "detected_supplier": preflight.detected_supplier if preflight else None,
                    "detected_date": preflight.detected_date if preflight else None,
                    "detected_albaran_number": preflight.detected_albaran_number if preflight else None,
                }
            )

    uploads.sort(key=lambda item: item["uploaded_at_sort"], reverse=True)
    for upload in uploads:
        upload.pop("uploaded_at_sort", None)
    return uploads


@router.get("/", response_class=HTMLResponse, include_in_schema=False, name="index")
@router.get("/login", response_class=HTMLResponse, include_in_schema=False, name="login")
async def landing_page(request: Request) -> Response:
    if request.headers.get("X-MS-TOKEN-AAD-ID-TOKEN") or getattr(request.state, "authenticated_user", None) is not None:
        return RedirectResponse(url=POST_LOGIN_REDIRECT_PATH, status_code=307)

    return request.app.state.templates.TemplateResponse(
        request,
        "pages/login.html",
        {
            "request": request,
            "page_title": "Iniciar sesión · Verdecora Upload Web",
            "login_url": _microsoft_login_url(request),
            "flash_messages": getattr(request.state, "flash_messages", []),
        },
    )


@router.get("/dashboard", response_class=HTMLResponse, name="dashboard")
async def dashboard(request: Request, current_user: CurrentUser) -> HTMLResponse:
    return request.app.state.templates.TemplateResponse(
        request,
        "pages/home.html",
        _build_template_context(
            request,
            current_user,
            page_title="Panel · Verdecora Upload Web",
        ),
    )


@router.get("/upload", response_class=HTMLResponse, name="upload_page")
@router.get("/uploads", response_class=HTMLResponse, include_in_schema=False)
async def upload_page(request: Request, current_user: CurrentUser) -> HTMLResponse:
    session = create_upload_session(user_oid=current_user.oid, user_name=current_user.name)
    return request.app.state.templates.TemplateResponse(
        request,
        "pages/upload.html",
        _build_template_context(
            request,
            current_user,
            page_title="Subir albarán · Verdecora Upload Web",
            session_id=session.session_id,
            files=session.files,
        ),
    )


@router.get("/mis-albaranes", response_class=HTMLResponse, name="my_uploads_page")
async def my_uploads_page(request: Request, current_user: CurrentUser) -> HTMLResponse:
    sessions = get_all_user_sessions(current_user.oid)
    uploads = _build_upload_rows(sessions)

    return request.app.state.templates.TemplateResponse(
        request,
        "pages/my_albaranes.html",
        _build_template_context(
            request,
            current_user,
            page_title="Mis albaranes · Verdecora Upload Web",
            uploads=uploads,
            status_options=STATUS_FILTERS,
        ),
    )


@router.get("/mis-albaranes/filter", response_class=HTMLResponse, name="my_uploads_filter")
async def my_uploads_filter(
    request: Request,
    current_user: CurrentUser,
    status_filter: str = "",
) -> HTMLResponse:
    sessions = get_all_user_sessions(current_user.oid)
    uploads = _build_upload_rows(sessions, status_filter)

    return request.app.state.templates.TemplateResponse(
        request,
        "pages/my_albaranes.html",
        _build_template_context(
            request,
            current_user,
            page_title="Mis albaranes · Verdecora Upload Web",
            uploads=uploads,
            status_filter=status_filter,
            status_options=STATUS_FILTERS,
        ),
    )


@router.get("/my-uploads")
async def my_uploads_partial(current_user: CurrentUser) -> dict[str, object]:
    return {
        "items": [],
        "user": {
            "oid": current_user.oid,
            "name": current_user.name,
        },
    }


@router.get("/upload/{session_id}/status", response_class=HTMLResponse, name="upload_status")
async def upload_status(request: Request, session_id: str, current_user: CurrentUser) -> HTMLResponse:
    """Show processing status with HTMX auto-refresh."""
    from src.upload_web.services.upload_session import get_upload_session

    session = get_upload_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.user_oid != current_user.oid:
        raise HTTPException(status_code=403, detail="Access denied.")

    total = len(session.files)
    completed = sum(1 for f in session.files if getattr(f, "processing_status", None) == "completed")
    progress = (completed / total * 100) if total > 0 else 0

    return request.app.state.templates.TemplateResponse(
        request,
        "pages/status.html",
        _build_template_context(
            request,
            current_user,
            page_title="Estado de procesamiento · Verdecora Upload Web",
            session=session,
            total=total,
            completed=completed,
            progress=round(progress, 1),
        ),
    )


@router.get("/upload/{session_id}/confirm-store", response_class=HTMLResponse, name="confirm_store")
async def confirm_store(request: Request, session_id: str, current_user: CurrentUser) -> HTMLResponse:
    """Show detected store, let user confirm or change."""
    from src.upload_web.services.upload_session import get_upload_session

    session = get_upload_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.user_oid != current_user.oid:
        raise HTTPException(status_code=403, detail="Access denied.")

    preflight = session.preflight
    return request.app.state.templates.TemplateResponse(
        request,
        "pages/confirm_store.html",
        _build_template_context(
            request,
            current_user,
            page_title="Confirmar tienda · Verdecora Upload Web",
            session=session,
            preflight=preflight,
        ),
    )


@router.get("/upload/{session_id}/summary", response_class=HTMLResponse, name="upload_summary")
async def upload_summary(request: Request, session_id: str, current_user: CurrentUser) -> HTMLResponse:
    """Show all uploaded files, preflight results, allow inline edits."""
    from src.upload_web.services.upload_session import get_upload_session

    session = get_upload_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.user_oid != current_user.oid:
        raise HTTPException(status_code=403, detail="Access denied.")

    return request.app.state.templates.TemplateResponse(
        request,
        "pages/summary.html",
        _build_template_context(
            request,
            current_user,
            page_title="Resumen de subida · Verdecora Upload Web",
            session=session,
        ),
    )
