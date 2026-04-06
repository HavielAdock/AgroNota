from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from app.auth import validar_token
from app.database import get_client
from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
from datetime import timezone
import io

router = APIRouter()


def validar_pfx(conteudo: bytes, senha: str) -> dict:
    try:
        senha_bytes = senha.encode("utf-8")
        chave, certificado, _ = load_key_and_certificates(conteudo, senha_bytes)

        if certificado is None:
            raise HTTPException(status_code=400, detail="Certificado inválido ou corrompido")

        subject = certificado.subject
        nome_titular = None
        cnpj_cert = None

        for attr in subject:
            if attr.oid.dotted_string == "2.5.4.3":
                nome_titular = attr.value
            if attr.oid.dotted_string == "2.5.4.5":
                cnpj_cert = attr.value

        validade = certificado.not_valid_after_utc if hasattr(certificado, "not_valid_after_utc") else certificado.not_valid_after.replace(tzinfo=timezone.utc)

        return {
            "titular": nome_titular,
            "cnpj_certificado": cnpj_cert,
            "validade": validade.isoformat(),
        }

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Senha incorreta ou arquivo inválido")


@router.post("/upload")
def upload_certificado(
    arquivo: UploadFile = File(...),
    senha: str = Form(...),
    usuario=Depends(validar_token)
):
    supabase = get_client()

    if not arquivo.filename.endswith((".pfx", ".p12")):
        raise HTTPException(status_code=400, detail="Arquivo deve ser .pfx ou .p12")

    conteudo = arquivo.file.read()

    # valida o certificado com a senha em memória — senha não é armazenada
    info = validar_pfx(conteudo, senha)

    # salva o arquivo no Supabase Storage (bucket privado)
    storage_path = f"{usuario['id']}/certificado.pfx"

    supabase.storage.from_("certificados").upload(
        path=storage_path,
        file=conteudo,
        file_options={"content-type": "application/x-pkcs12", "upsert": "true"}
    )

    # salva os metadados no banco (sem a senha)
    existente = supabase.table("certificados").select("id").eq("usuario_id", usuario["id"]).execute()

    if existente.data:
        resultado = supabase.table("certificados").update({
            "storage_path": storage_path,
            "titular": info["titular"],
            "cnpj_certificado": info["cnpj_certificado"],
            "validade": info["validade"],
        }).eq("usuario_id", usuario["id"]).execute()
    else:
        resultado = supabase.table("certificados").insert({
            "usuario_id": usuario["id"],
            "storage_path": storage_path,
            "titular": info["titular"],
            "cnpj_certificado": info["cnpj_certificado"],
            "validade": info["validade"],
        }).execute()

    if not resultado.data:
        raise HTTPException(status_code=500, detail="Erro ao salvar certificado")

    return {
        "mensagem": "Certificado enviado com sucesso",
        "titular": info["titular"],
        "cnpj_certificado": info["cnpj_certificado"],
        "validade": info["validade"],
    }


@router.get("/")
def status_certificado(usuario=Depends(validar_token)):
    supabase = get_client()
    resultado = supabase.table("certificados").select("titular, cnpj_certificado, validade, criado_em").eq("usuario_id", usuario["id"]).execute()

    if not resultado.data:
        return {"certificado": None, "mensagem": "Nenhum certificado cadastrado"}

    from datetime import datetime
    cert = resultado.data[0]
    validade = datetime.fromisoformat(cert["validade"])
    agora = datetime.now(timezone.utc)
    dias_restantes = (validade - agora).days

    alerta = None
    if dias_restantes < 0:
        alerta = "🔴 Certificado VENCIDO. Faça upload de um novo certificado."
    elif dias_restantes <= 7:
        alerta = f"🔴 URGENTE: Certificado vence em {dias_restantes} dias."
    elif dias_restantes <= 30:
        alerta = f"⚠️ Certificado vence em {dias_restantes} dias. Providencie renovação."

    return {
        "certificado": cert,
        "dias_restantes": dias_restantes,
        "alerta": alerta,
    }


@router.delete("/")
def remover_certificado(usuario=Depends(validar_token)):
    supabase = get_client()
    storage_path = f"{usuario['id']}/certificado.pfx"
    supabase.storage.from_("certificados").remove([storage_path])
    supabase.table("certificados").delete().eq("usuario_id", usuario["id"]).execute()
    return {"mensagem": "Certificado removido com sucesso"}