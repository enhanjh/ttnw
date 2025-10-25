from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.api_clients.hantoo_client import HantooClient

router = APIRouter(
    prefix="/api/auth",
    tags=["auth"],
)

class AuthRequest(BaseModel):
    appkey: str
    appsecret: str

@router.post("/token")
async def get_auth_token(request: AuthRequest):
    try:
        result = hantoo_auth.auth(appkey=request.appkey, appsecret=request.appsecret)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        import traceback
        traceback.print_exc() # Print traceback to server console
        raise HTTPException(status_code=500, detail=str(e))