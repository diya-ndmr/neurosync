from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.module import Module
from app.models.user import User, UserRole
from app.schemas.record_schema import ModuleCreate
from app.middleware.security import get_current_user, require_role

router = APIRouter(prefix="/api/modules", tags=["Modules"])


@router.get("/")
def list_modules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    modules = db.query(Module).order_by(Module.module_name).all()
    return [
        {
            "id": m.id,
            "module_code": m.module_code,
            "module_name": m.module_name,
            "faculty": m.faculty,
        }
        for m in modules
    ]


@router.post("/")
def create_module(
    data: ModuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    module_code = data.module_code.strip().upper()
    if db.query(Module.id).filter(Module.module_code == module_code).first():
        raise HTTPException(status_code=409, detail=f"Module code {module_code} already exists")
    module = Module(module_code=module_code, module_name=data.module_name.strip(), faculty=data.faculty.strip())
    db.add(module)
    try:
        db.commit()
    except IntegrityError:
        # Concurrent insert of the same code: report it instead of a 500.
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Module code {module_code} already exists")
    db.refresh(module)
    return {"message": "Module created", "id": module.id}
