from fastapi import APIRouter, Depends, HTTPException
from app.auth import validar_token
from app.database import get_client
from app.models import ClienteCreate, ClienteOutput

router = APIRouter()


@router.post("/", response_model=ClienteOutput)
def criar_cliente(dados: ClienteCreate, usuario=Depends(validar_token)):
    supabase = get_client()
    try:
        resultado = supabase.table("clientes").insert({
            **dados.model_dump(),
            "usuario_id": usuario["id"]
        }).execute()
        if not resultado.data:
            raise HTTPException(status_code=400, detail="Erro ao criar cliente")
        return resultado.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
def listar_clientes(usuario=Depends(validar_token)):
    supabase = get_client()
    resultado = supabase.table("clientes").select("*").eq("usuario_id", usuario["id"]).execute()
    return resultado.data


@router.get("/{cliente_id}")
def buscar_cliente(cliente_id: str, usuario=Depends(validar_token)):
    supabase = get_client()
    resultado = supabase.table("clientes").select("*").eq("id", cliente_id).eq("usuario_id", usuario["id"]).single().execute()
    if not resultado.data:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return resultado.data


@router.put("/{cliente_id}")
def atualizar_cliente(cliente_id: str, dados: ClienteCreate, usuario=Depends(validar_token)):
    supabase = get_client()
    resultado = supabase.table("clientes").update(dados.model_dump()).eq("id", cliente_id).eq("usuario_id", usuario["id"]).execute()
    if not resultado.data:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return resultado.data[0]


@router.delete("/{cliente_id}")
def deletar_cliente(cliente_id: str, usuario=Depends(validar_token)):
    supabase = get_client()
    supabase.table("clientes").delete().eq("id", cliente_id).eq("usuario_id", usuario["id"]).execute()
    return {"mensagem": "Cliente removido"}