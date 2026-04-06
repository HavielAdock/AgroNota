from fastapi import APIRouter, Depends, HTTPException
from app.auth import validar_token
from app.database import get_client
from app.models import ProdutoCreate, ProdutoOutput

router = APIRouter()


@router.post("/", response_model=ProdutoOutput)
def criar_produto(dados: ProdutoCreate, usuario=Depends(validar_token)):
    supabase = get_client()
    try:
        resultado = supabase.table("produtos").insert({
            **dados.model_dump(),
            "usuario_id": usuario["id"]
        }).execute()
        if not resultado.data:
            raise HTTPException(status_code=400, detail="Erro ao criar produto")
        return resultado.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
def listar_produtos(usuario=Depends(validar_token)):
    supabase = get_client()
    resultado = supabase.table("produtos").select("*").eq("usuario_id", usuario["id"]).execute()
    return resultado.data


@router.get("/{produto_id}")
def buscar_produto(produto_id: str, usuario=Depends(validar_token)):
    supabase = get_client()
    resultado = supabase.table("produtos").select("*").eq("id", produto_id).eq("usuario_id", usuario["id"]).single().execute()
    if not resultado.data:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return resultado.data


@router.put("/{produto_id}")
def atualizar_produto(produto_id: str, dados: ProdutoCreate, usuario=Depends(validar_token)):
    supabase = get_client()
    resultado = supabase.table("produtos").update(dados.model_dump()).eq("id", produto_id).eq("usuario_id", usuario["id"]).execute()
    if not resultado.data:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return resultado.data[0]


@router.delete("/{produto_id}")
def deletar_produto(produto_id: str, usuario=Depends(validar_token)):
    supabase = get_client()
    supabase.table("produtos").delete().eq("id", produto_id).eq("usuario_id", usuario["id"]).execute()
    return {"mensagem": "Produto removido"}