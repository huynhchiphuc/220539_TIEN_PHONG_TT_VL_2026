from datetime import datetime
from pathlib import Path
import re
import shutil
import traceback

from fastapi import APIRouter, Depends, Query, HTTPException

from app.db.query_helpers import db_cursor, fetch_all
from app.security.security import get_current_user
from app.services.comic.session_access import ensure_session_owner
from app.services.comic.file_ops import (
    OUTPUT_FOLDER,
    UPLOAD_FOLDER,
    create_media_access_token,
)
from app.config import settings

router = APIRouter(prefix="/comic", tags=["comic"])


@router.get("/projects")
async def get_user_projects(user: dict = Depends(get_current_user)):
    projects = []
    user_id = user.get("id")

    try:
        user_sessions = fetch_all(
            """
            SELECT session_id, MAX(created_at) as max_created_at
            FROM upload_sessions
            WHERE user_id = %s
            GROUP BY session_id
            ORDER BY max_created_at DESC
            """,
            (user_id,),
            dictionary=True,
        )

        if not user_sessions:
            return {"projects": [], "total": 0, "user_id": user_id}

        session_ids = [s["session_id"] for s in user_sessions]

    except Exception as exc:
        print(f"⚠️ Database query error: {exc}")
        return {"projects": [], "total": 0, "user_id": user_id}

    outputs_dir = Path(OUTPUT_FOLDER)

    for session_id in session_ids:
        session_folder = outputs_dir / session_id

        thumbnail = None
        has_covers = False
        page_count = 0
        total_size = 0
        status = "expired"

        session_record = next((s for s in user_sessions if s["session_id"] == session_id), None)
        created_at_dt = (
            session_record.get("max_created_at")
            if session_record and "max_created_at" in session_record
            else (session_record.get("created_at") if session_record else datetime.now())
        )
        created_at = created_at_dt.isoformat() if isinstance(created_at_dt, datetime) else str(created_at_dt)
        modified_at = created_at

        if session_folder.exists() and session_folder.is_dir():
            pages = list(session_folder.glob("page_*.*"))
            page_count = len([p for p in pages if p.suffix.lower() in [".jpg", ".jpeg", ".png"]])

            for ext in [".jpg", ".jpeg", ".png"]:
                thumb_path = session_folder / f"page_001{ext}"
                if thumb_path.exists():
                    media_token = create_media_access_token(session_id, user_id, settings.SECRET_KEY)
                    thumbnail = f"/api/v1/comic/sessions/{session_id}/outputs/page_001{ext}?st={media_token}"
                    break

            covers_dir = session_folder / "covers"
            has_covers = covers_dir.exists() and any(covers_dir.iterdir())

            created_at = datetime.fromtimestamp(session_folder.stat().st_ctime).isoformat()
            modified_at = datetime.fromtimestamp(session_folder.stat().st_mtime).isoformat()

            total_size = sum(file.stat().st_size for file in session_folder.rglob("*") if file.is_file())
            status = "completed" if page_count > 0 else "incomplete"

        size_mb = round(total_size / (1024 * 1024), 2)

        projects.append(
            {
                "session_id": session_id,
                "page_count": page_count,
                "thumbnail": thumbnail,
                "has_covers": has_covers,
                "created_at": created_at,
                "modified_at": modified_at,
                "size_mb": size_mb,
                "status": status,
            }
        )

    return {
        "projects": projects,
        "total": len(projects),
        "user_id": user_id,
        "username": user.get("username"),
    }


@router.delete("/projects/{session_id}")
async def delete_project(session_id: str, user: dict = Depends(get_current_user)):
    ensure_session_owner(session_id, user)

    try:
        with db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM upload_sessions WHERE session_id = %s", (session_id,))
            cursor.execute("DELETE FROM comic_projects WHERE session_id = %s", (session_id,))
    except Exception as db_err:
        print(f"Error deleting from DB: {db_err}")

    session_folder = Path(OUTPUT_FOLDER) / session_id
    if session_folder.exists():
        try:
            shutil.rmtree(session_folder)
        except Exception as file_err:
            print(f"Error deleting folder: {file_err}")

    upload_folder = Path(UPLOAD_FOLDER) / session_id
    if upload_folder.exists():
        try:
            shutil.rmtree(upload_folder)
        except Exception:
            pass

    return {
        "success": True,
        "message": f"Đã xóa project {session_id}",
        "session_id": session_id,
    }


@router.get("/activity")
@router.get("/user/activity")
async def get_user_activity_history(
    limit: int = Query(20, ge=1, le=200),
    user: dict = Depends(get_current_user),
):
    try:
        activities = fetch_all(
            """
            SELECT
                id,
                action AS action_type,
                resource_type,
                session_id,
                details,
                ip_address,
                user_agent,
                created_at AS timestamp
            FROM activity_logs
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (user.get("id"), limit),
            dictionary=True,
        )
        enriched_activities = []

        for activity in activities:
            details_str = activity.get("details", "") or ""
            enriched = {
                "id": activity["id"],
                "action_type": activity["action_type"],
                "session_id": activity.get("session_id"),
                "details": details_str,
                "timestamp": activity["timestamp"].isoformat() if activity["timestamp"] else None,
                "ip_address": activity.get("ip_address"),
                "user_agent": activity.get("user_agent"),
                "image_count": 0,
                "layout_mode": None,
                "status": "success",
            }

            if details_str and "image" in details_str.lower():
                match = re.search(r"(\d+)\s*(?:ảnh|image)", details_str.lower())
                if match:
                    enriched["image_count"] = int(match.group(1))

            if details_str:
                if "simple" in details_str.lower():
                    enriched["layout_mode"] = "simple"
                elif "advanced" in details_str.lower():
                    enriched["layout_mode"] = "advanced"

            enriched_activities.append(enriched)

        return {
            "success": True,
            "activities": enriched_activities,
            "total": len(enriched_activities),
            "user_id": user.get("id"),
        }

    except Exception as exc:
        print(f"Activity log error: {str(exc)}")
        return {
            "success": True,
            "activities": [],
            "total": 0,
            "message": "Activity logging not available yet",
        }


@router.get("/dashboard")
@router.get("/user/dashboard")
async def get_dashboard_stats(user: dict = Depends(get_current_user)):
    user_id = user.get("id")

    try:
        projects = []
        total_projects = 0
        total_pages = 0
        total_size_mb = 0.0

        try:
            user_sessions_db = fetch_all(
                """
                SELECT session_id, MAX(created_at) as created_at
                FROM upload_sessions
                WHERE user_id = %s
                GROUP BY session_id
                ORDER BY created_at DESC
                """,
                (user_id,),
                dictionary=True,
            )

            outputs_dir = Path(OUTPUT_FOLDER)
            for session in user_sessions_db:
                session_id = session["session_id"]
                created_at_dt = session.get("created_at") or datetime.now()
                created_at_str = created_at_dt.isoformat() if isinstance(created_at_dt, datetime) else str(created_at_dt)

                session_dir = outputs_dir / session_id
                page_count = 0
                size_mb = 0.0

                if session_dir.is_dir():
                    page_files = (
                        list(session_dir.glob("page_*.jpg"))
                        + list(session_dir.glob("page_*.png"))
                    )
                    page_count = len(page_files)

                    try:
                        total_bytes = sum(file.stat().st_size for file in session_dir.rglob("*") if file.is_file())
                        size_mb = total_bytes / (1024 * 1024)
                    except Exception:
                        pass

                projects.append(
                    {
                        "session_id": session_id,
                        "page_count": page_count,
                        "size_mb": size_mb,
                        "created_at": created_at_str,
                    }
                )

            total_projects = len(projects)
            total_pages = sum(item["page_count"] for item in projects)
            total_size_mb = sum(item["size_mb"] for item in projects)

            recent_activities = fetch_all(
                """
                SELECT action AS action_type, details, created_at AS timestamp
                FROM activity_logs
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 5
                """,
                (user_id,),
                dictionary=True,
            )

            activity_breakdown_list = fetch_all(
                """
                SELECT action AS action_type, COUNT(*) as count
                FROM activity_logs
                WHERE user_id = %s
                GROUP BY action
                """,
                (user_id,),
                dictionary=True,
            )
            activity_breakdown = {item["action_type"]: item["count"] for item in activity_breakdown_list}

            total_row = fetch_all(
                "SELECT COUNT(*) as total FROM activity_logs WHERE user_id = %s",
                (user_id,),
                dictionary=True,
            )
            total_activities = total_row[0]["total"] if total_row else 0

            user_info = fetch_all(
                "SELECT username, email, created_at, last_login FROM users WHERE id = %s",
                (user_id,),
                dictionary=True,
            )
            user_info = user_info[0] if user_info else None

            return {
                "success": True,
                "total_projects": total_projects,
                "total_pages": total_pages,
                "total_size_mb": round(total_size_mb, 2),
                "total_activities": total_activities,
                "recent_projects": sorted(projects, key=lambda item: item["created_at"], reverse=True)[:5],
                "recent_activities": [
                    {
                        "action_type": activity["action_type"],
                        "details": activity["details"],
                        "timestamp": activity["timestamp"].isoformat() if activity["timestamp"] else None,
                    }
                    for activity in recent_activities
                ],
                "activity_breakdown": activity_breakdown,
                "user_name": user_info["username"] if user_info else user.get("username"),
                "user_email": user_info["email"] if user_info else user.get("email"),
                "user_created_at": user_info["created_at"].isoformat() if user_info and user_info["created_at"] else None,
                "user_last_login": user_info["last_login"].isoformat() if user_info and user_info["last_login"] else None,
            }
        except Exception as db_error:
            print(f"Database error: {str(db_error)}")
            return {
                "success": True,
                "total_projects": total_projects,
                "total_pages": total_pages,
                "total_size_mb": total_size_mb,
                "total_activities": 0,
                "recent_projects": sorted(projects, key=lambda item: item["created_at"], reverse=True)[:5],
                "recent_activities": [],
                "activity_breakdown": {},
                "user_name": user.get("username"),
                "user_email": user.get("email"),
                "user_created_at": None,
                "user_last_login": None,
            }

    except Exception as exc:
        print(f"Dashboard error: {str(exc)}")
        traceback.print_exc()
        return {
            "success": True,
            "total_projects": 0,
            "total_pages": 0,
            "total_size_mb": 0,
            "total_activities": 0,
            "recent_projects": [],
            "recent_activities": [],
            "activity_breakdown": {},
            "user_name": user.get("username", "Unknown"),
            "user_email": user.get("email", "Unknown"),
            "message": f"Dashboard limited - {str(exc)}",
        }
