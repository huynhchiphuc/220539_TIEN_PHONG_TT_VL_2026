from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
from typing import Optional
import mysql.connector
from pydantic import BaseModel
from app.config import settings
from app.security.security import get_admin_user
from app.utils.mysql_connection import get_mysql_connection

router = APIRouter(prefix="/admin", tags=["admin"])


# ==================== Helper Functions ====================
def get_db_connection():
    return get_mysql_connection()


# ==================== Pydantic Models ====================
class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


# ==================== DASHBOARD STATS ====================
@router.get("/stats/dashboard")
def get_dashboard_stats(admin=Depends(get_admin_user)):
    """Get overview statistics for admin dashboard"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Total users
        cursor.execute("SELECT COUNT(*) as count FROM users")
        total_users = cursor.fetchone()["count"]
        
        # Active users (logged in last 7 days)
        cursor.execute("""
            SELECT COUNT(*) as count FROM users 
            WHERE last_login >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        """)
        active_users = cursor.fetchone()["count"]
        
        # Total comic projects
        cursor.execute("SELECT COUNT(*) as count FROM comic_projects")
        total_projects = cursor.fetchone()["count"]
        
        # Projects created this month
        cursor.execute("""
            SELECT COUNT(*) as count FROM comic_projects 
            WHERE MONTH(created_at) = MONTH(NOW()) AND YEAR(created_at) = YEAR(NOW())
        """)
        monthly_projects = cursor.fetchone()["count"]
        
        # Total uploaded images
        cursor.execute("SELECT COUNT(*) as count FROM uploaded_images")
        total_images = cursor.fetchone()["count"]
        
        # New users this month
        cursor.execute("""
            SELECT COUNT(*) as count FROM users 
            WHERE MONTH(created_at) = MONTH(NOW()) AND YEAR(created_at) = YEAR(NOW())
        """)
        monthly_users = cursor.fetchone()["count"]
        
        # User growth (last 6 months)
        cursor.execute("""
            SELECT 
                DATE_FORMAT(created_at, '%Y-%m') as month,
                COUNT(*) as count
            FROM users 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
            GROUP BY DATE_FORMAT(created_at, '%Y-%m')
            ORDER BY month
        """)
        user_growth = cursor.fetchall()
        
        # Project growth (last 6 months)
        cursor.execute("""
            SELECT 
                DATE_FORMAT(created_at, '%Y-%m') as month,
                COUNT(*) as count
            FROM comic_projects 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
            GROUP BY DATE_FORMAT(created_at, '%Y-%m')
            ORDER BY month
        """)
        project_growth = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return {
            "overview": {
                "total_users": total_users,
                "active_users": active_users,
                "total_projects": total_projects,
                "monthly_projects": monthly_projects,
                "total_images": total_images,
                "monthly_users": monthly_users
            },
            "growth": {
                "users": user_growth,
                "projects": project_growth
            }
        }
    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# ==================== USER MANAGEMENT ====================
@router.get("/users")
def get_all_users(
    admin=Depends(get_admin_user),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None
):
    """Get all users with pagination and filters"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Build query with filters
        where_clauses = []
        params = []
        
        if search:
            where_clauses.append("(username LIKE %s OR email LIKE %s)")
            params.extend([f"%{search}%", f"%{search}%"])
        
        if role:
            where_clauses.append("role = %s")
            params.append(role)
        
        if is_active is not None:
            where_clauses.append("is_active = %s")
            params.append(is_active)
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # Get total count
        cursor.execute(f"SELECT COUNT(*) as count FROM users WHERE {where_sql}", params)
        total = cursor.fetchone()["count"]
        
        # Get paginated users
        offset = (page - 1) * limit
        cursor.execute(f"""
            SELECT 
                id, username, email, role, is_active, 
                avatar_url, oauth_provider, created_at, last_login
            FROM users 
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """, params + [limit, offset])
        
        users = cursor.fetchall()
        
        # Convert datetime to string
        for user in users:
            if user.get("created_at"):
                user["created_at"] = user["created_at"].isoformat()
            if user.get("last_login"):
                user["last_login"] = user["last_login"].isoformat()
        
        cursor.close()
        conn.close()
        
        return {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit,
            "users": users
        }
    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/users/{user_id}")
def get_user_detail(user_id: int, admin=Depends(get_admin_user)):
    """Get detailed information about a specific user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get user info
        cursor.execute("""
            SELECT 
                id, username, email, role, is_active, avatar_url,
                oauth_provider, created_at, updated_at, last_login
            FROM users WHERE id = %s
        """, (user_id,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get user's project count
        cursor.execute("""
            SELECT COUNT(*) as count FROM comic_projects WHERE user_id = %s
        """, (user_id,))
        project_count = cursor.fetchone()["count"]
        
        # Get user's recent projects
        cursor.execute("""
            SELECT id, title, status, created_at, updated_at
            FROM comic_projects 
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 5
        """, (user_id,))
        recent_projects = cursor.fetchall()
        
        # Convert datetime to string
        if user.get("created_at"):
            user["created_at"] = user["created_at"].isoformat()
        if user.get("updated_at"):
            user["updated_at"] = user["updated_at"].isoformat()
        if user.get("last_login"):
            user["last_login"] = user["last_login"].isoformat()
        
        for project in recent_projects:
            if project.get("created_at"):
                project["created_at"] = project["created_at"].isoformat()
            if project.get("updated_at"):
                project["updated_at"] = project["updated_at"].isoformat()
        
        cursor.close()
        conn.close()
        
        return {
            "user": user,
            "project_count": project_count,
            "recent_projects": recent_projects
        }
    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.put("/users/{user_id}")
def update_user(user_id: int, user_update: UserUpdate, admin=Depends(get_admin_user)):
    """Update user information (admin only)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="User not found")
        
        # Build update query dynamically
        update_fields = []
        params = []
        
        if user_update.username is not None:
            update_fields.append("username = %s")
            params.append(user_update.username)
        
        if user_update.email is not None:
            update_fields.append("email = %s")
            params.append(user_update.email)
        
        if user_update.role is not None:
            if user_update.role not in ["user", "admin"]:
                raise HTTPException(status_code=400, detail="Invalid role")
            update_fields.append("role = %s")
            params.append(user_update.role)
        
        if user_update.is_active is not None:
            update_fields.append("is_active = %s")
            params.append(user_update.is_active)
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # Add updated_at
        update_fields.append("updated_at = %s")
        params.append(datetime.now())
        
        # Execute update
        params.append(user_id)
        cursor.execute(f"""
            UPDATE users 
            SET {', '.join(update_fields)}
            WHERE id = %s
        """, params)
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return {"message": "✅ User updated successfully"}
    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.delete("/users/{user_id}")
def delete_user(user_id: int, admin=Depends(get_admin_user)):
    """Delete a user (admin only)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="User not found")
        
        # Prevent deleting yourself
        if user_id == admin["id"]:
            raise HTTPException(status_code=400, detail="Cannot delete your own account")
        
        # Delete user (cascade will handle related records)
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return {"message": "✅ User deleted successfully"}
    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# ==================== ACTIVITY LOGS ====================
@router.get("/logs/activities")
def get_activity_logs(
    admin=Depends(get_admin_user),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200)
):
    """Get recent activity logs"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get total count
        cursor.execute("SELECT COUNT(*) as count FROM activity_logs")
        total = cursor.fetchone()["count"]
        
        # Get paginated logs
        offset = (page - 1) * limit
        cursor.execute("""
            SELECT 
                al.id, al.action, al.details, al.ip_address,
                al.user_agent, al.created_at,
                u.username, u.email
            FROM activity_logs al
            LEFT JOIN users u ON al.user_id = u.id
            ORDER BY al.created_at DESC
            LIMIT %s OFFSET %s
        """, (limit, offset))
        
        logs = cursor.fetchall()
        
        # Convert datetime to string
        for log in logs:
            if log.get("created_at"):
                log["created_at"] = log["created_at"].isoformat()
        
        cursor.close()
        conn.close()
        
        return {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit,
            "logs": logs
        }
    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# ==================== COMIC PROJECTS MANAGEMENT ====================
@router.get("/projects")
def get_all_projects(
    admin=Depends(get_admin_user),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None
):
    """Get all comic projects with pagination"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Build query
        where_clause = "status = %s" if status else "1=1"
        params = [status] if status else []
        
        # Get total count
        cursor.execute(f"SELECT COUNT(*) as count FROM comic_projects WHERE {where_clause}", params)
        total = cursor.fetchone()["count"]
        
        # Get paginated projects
        offset = (page - 1) * limit
        cursor.execute(f"""
            SELECT 
                cp.id, cp.project_name, cp.status, cp.total_pages,
                cp.layout_mode, cp.created_at, cp.updated_at,
                u.username, u.email
            FROM comic_projects cp
            LEFT JOIN users u ON cp.user_id = u.id
            WHERE {where_clause}
            ORDER BY cp.created_at DESC
            LIMIT %s OFFSET %s
        """, params + [limit, offset])
        
        projects = cursor.fetchall()
        
        # Convert datetime to string
        for project in projects:
            if project.get("created_at"):
                project["created_at"] = project["created_at"].isoformat()
            if project.get("updated_at"):
                project["updated_at"] = project["updated_at"].isoformat()
        
        cursor.close()
        conn.close()
        
        return {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit,
            "projects": projects
        }
    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.delete("/projects/{project_id}")
def delete_project(project_id: int, admin=Depends(get_admin_user)):
    """Delete a comic project (admin only)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check if project exists
        cursor.execute("SELECT id FROM comic_projects WHERE id = %s", (project_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Delete project (cascade will handle pages)
        cursor.execute("DELETE FROM comic_projects WHERE id = %s", (project_id,))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return {"message": "✅ Project deleted successfully"}
    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# ==================== SYSTEM INFO ====================
@router.get("/system/info")
def get_system_info(admin=Depends(get_admin_user)):
    """Get system information"""
    import platform
    import psutil
    
    return {
        "platform": {
            "os": platform.system(),
            "version": platform.version(),
            "python_version": platform.python_version()
        },
        "resources": {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        }
    }
