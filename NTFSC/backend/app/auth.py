from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

from app.database import get_client

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 8

security = HTTPBearer()


def gerar_token(usuario_id: str, email: str) -> str:
    payload = {
        "sub": usuario_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def validar_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        usuario_id: str = payload.get("sub")
        email: str = payload.get("email")
        if not usuario_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
        return {"id": usuario_id, "email": email}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido ou expirado")


def login(email: str, senha: str) -> dict:
    supabase = get_client()
    try:
        resposta = supabase.auth.sign_in_with_password({"email": email, "password": senha})
        if not resposta.user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha incorretos")
        usuario_id = resposta.user.id
        dados = supabase.table("usuarios").select("*").eq("id", usuario_id).single().execute()
        if not dados.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
        token = gerar_token(usuario_id, email)
        return {"access_token": token, "token_type": "bearer", "usuario": dados.data}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha incorretos")


def registrar(dados_usuario: dict) -> dict:
    supabase = get_client()
    email = dados_usuario.get("email")
    senha = dados_usuario.pop("senha")
    try:
        auth_resp = supabase.auth.admin.create_user({"email": email, "password": senha, "email_confirm": True})
        if not auth_resp.user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Erro ao criar usuário")
        usuario_id = auth_resp.user.id
        dados_usuario["id"] = usuario_id
        resultado = supabase.table("usuarios").insert(dados_usuario).execute()
        if not resultado.data:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao salvar usuário")
        token = gerar_token(usuario_id, email)
        return {"access_token": token, "token_type": "bearer", "usuario": resultado.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Erro: {str(e)}")