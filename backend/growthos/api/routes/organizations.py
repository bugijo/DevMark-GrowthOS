from fastapi import APIRouter, Depends

from growthos.dependencies import AuthContext, get_current_context
from growthos.schemas import OrganizationRead

router = APIRouter()


@router.get("/current", response_model=OrganizationRead)
def current_organization(context: AuthContext = Depends(get_current_context)) -> OrganizationRead:
    return OrganizationRead.model_validate(context.organization)
