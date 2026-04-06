from fastapi import APIRouter, Depends, HTTPException
from app.auth import validar_token
from app.database import get_client
from app.models import EmitirNotaInput

router = APIRouter()


# ─── TABELA DE ALÍQUOTAS INTERESTADUAIS ──────────────────────

ALIQUOTAS_INTERESTADUAIS = {
    "AC": 12, "AL": 12, "AP": 12, "AM": 12, "BA": 12,
    "CE": 12, "MA": 12, "PA": 12, "PB": 12, "PE": 12,
    "PI": 12, "RN": 12, "RO": 12, "RR": 12, "SE": 12,
    "TO": 12, "DF": 12, "GO": 12, "MS": 12, "MT": 12,
    "ES": 12, "MG": 7,  "PR": 7,  "RJ": 7,  "RS": 7,
    "SC": 7,  "SP": 7,
}

ALIQUOTAS_INTERNAS = {
    "AC": 17, "AL": 17, "AP": 18, "AM": 18, "BA": 18,
    "CE": 18, "DF": 18, "ES": 17, "GO": 17, "MA": 18,
    "MT": 17, "MS": 17, "MG": 18, "PA": 17, "PB": 18,
    "PR": 19, "PE": 18, "PI": 18, "RJ": 20, "RN": 18,
    "RS": 17, "RO": 17, "RR": 17, "SC": 17, "SP": 18,
    "SE": 18, "TO": 18,
}


# ─── LÓGICA FISCAL ───────────────────────────────────────────

def calcular_fiscal(uf_emitente: str, uf_destinatario: str, is_contribuinte: bool, valor_total: float, tem_beneficio: bool):

    operacao_interna = uf_emitente == uf_destinatario

    # CFOP MVP: apenas 5.105 e 6.105
    cfop = "5.105" if operacao_interna else "6.105"

    # ICMS
    if tem_beneficio:
        icms_aliquota = 0.0
        icms_valor = 0.0
    elif operacao_interna:
        icms_aliquota = ALIQUOTAS_INTERNAS.get(uf_emitente, 18)
        icms_valor = round(valor_total * icms_aliquota / 100, 2)
    else:
        icms_aliquota = ALIQUOTAS_INTERESTADUAIS.get(uf_destinatario, 12)
        icms_valor = round(valor_total * icms_aliquota / 100, 2)

    # DIFAL e GNRE
    difal_valor = 0.0
    gnre_necessaria = False

    if not operacao_interna and not is_contribuinte:
        aliq_interna_destino = ALIQUOTAS_INTERNAS.get(uf_destinatario, 18)
        aliq_interestadual = ALIQUOTAS_INTERESTADUAIS.get(uf_destinatario, 12)
        difal_valor = round(valor_total * (aliq_interna_destino - aliq_interestadual) / 100, 2)
        if difal_valor > 0:
            gnre_necessaria = True

    return {
        "cfop": cfop,
        "operacao": "interna" if operacao_interna else "interestadual",
        "icms_aliquota": icms_aliquota if not tem_beneficio else 0,
        "icms_valor": icms_valor,
        "difal_valor": difal_valor,
        "gnre_necessaria": gnre_necessaria,
        "gnre_valor": difal_valor if gnre_necessaria else 0,
    }


# ─── ROTAS ───────────────────────────────────────────────────

@router.post("/calcular")
def calcular_nota(dados: EmitirNotaInput, usuario=Depends(validar_token)):
    supabase = get_client()

    # busca emitente
    emitente = supabase.table("usuarios").select("uf").eq("id", usuario["id"]).single().execute()
    if not emitente.data:
        raise HTTPException(status_code=404, detail="Emitente não encontrado")

    # busca cliente
    cliente = supabase.table("clientes").select("*").eq("id", dados.cliente_id).eq("usuario_id", usuario["id"]).single().execute()
    if not cliente.data:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    # busca produto
    produto = supabase.table("produtos").select("*").eq("id", dados.produto_id).eq("usuario_id", usuario["id"]).single().execute()
    if not produto.data:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    valor_total = round(dados.quantidade * dados.valor_unitario, 2)

    fiscal = calcular_fiscal(
        uf_emitente=emitente.data["uf"],
        uf_destinatario=cliente.data["uf"],
        is_contribuinte=cliente.data.get("is_contribuinte", False),
        valor_total=valor_total,
        tem_beneficio=produto.data.get("tem_beneficio_fiscal", False),
    )

    return {
        "cliente": cliente.data,
        "produto": produto.data,
        "quantidade": dados.quantidade,
        "valor_unitario": dados.valor_unitario,
        "valor_total": valor_total,
        **fiscal,
        "aviso_gnre": (
            f"⚠️ ATENÇÃO: Esta venda exige recolhimento de GNRE no valor de R$ {fiscal['gnre_valor']:.2f} "
            f"para o estado de {cliente.data['uf']} antes do transporte. "
            f"O não recolhimento pode resultar em multa e apreensão da mercadoria."
        ) if fiscal["gnre_necessaria"] else None,
    }


@router.post("/emitir")
def emitir_nota(dados: EmitirNotaInput, gnre_ciente: bool = False, usuario=Depends(validar_token)):
    supabase = get_client()

    # busca emitente
    emitente = supabase.table("usuarios").select("*").eq("id", usuario["id"]).single().execute()
    if not emitente.data:
        raise HTTPException(status_code=404, detail="Emitente não encontrado")

    # busca cliente
    cliente = supabase.table("clientes").select("*").eq("id", dados.cliente_id).eq("usuario_id", usuario["id"]).single().execute()
    if not cliente.data:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    # busca produto
    produto = supabase.table("produtos").select("*").eq("id", dados.produto_id).eq("usuario_id", usuario["id"]).single().execute()
    if not produto.data:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    valor_total = round(dados.quantidade * dados.valor_unitario, 2)

    fiscal = calcular_fiscal(
        uf_emitente=emitente.data["uf"],
        uf_destinatario=cliente.data["uf"],
        is_contribuinte=cliente.data.get("is_contribuinte", False),
        valor_total=valor_total,
        tem_beneficio=produto.data.get("tem_beneficio_fiscal", False),
    )

    # próximo número de nota
    ultima = supabase.table("notas_fiscais").select("numero").eq("usuario_id", usuario["id"]).order("numero", desc=True).limit(1).execute()
    proximo_numero = (ultima.data[0]["numero"] + 1) if ultima.data else 1

    # salva a nota
    nota = supabase.table("notas_fiscais").insert({
        "usuario_id": usuario["id"],
        "cliente_id": dados.cliente_id,
        "numero": proximo_numero,
        "serie": "001",
        "status": "pendente",
        "cfop": fiscal["cfop"],
        "valor_total": valor_total,
        "valor_icms": fiscal["icms_valor"],
        "valor_difal": fiscal["difal_valor"],
        "gnre_necessaria": fiscal["gnre_necessaria"],
        "gnre_valor": fiscal["gnre_valor"],
        "gnre_recolhida": gnre_ciente,
        "ambiente": "homologacao",
    }).execute()

    if not nota.data:
        raise HTTPException(status_code=500, detail="Erro ao salvar nota")

    nota_id = nota.data[0]["id"]

    # salva o item
    supabase.table("itens_nota").insert({
        "nota_id": nota_id,
        "produto_id": dados.produto_id,
        "quantidade": dados.quantidade,
        "valor_unitario": dados.valor_unitario,
        "valor_total": valor_total,
        "icms_aliquota": fiscal["icms_aliquota"],
        "icms_valor": fiscal["icms_valor"],
    }).execute()

    resposta = {
        "mensagem": "Nota fiscal registrada com sucesso",
        "nota": nota.data[0],
        "fiscal": fiscal,
    }

    if fiscal["gnre_necessaria"] and not gnre_ciente:
        resposta["aviso_gnre"] = (
            f"🔴 ATENÇÃO: Você precisa recolher uma GNRE de R$ {fiscal['gnre_valor']:.2f} "
            f"para {cliente.data['uf']} antes de transportar a mercadoria. "
            f"O não recolhimento pode resultar em MULTA e APREENSÃO da carga."
        )

    return resposta


@router.get("/")
def listar_notas(usuario=Depends(validar_token)):
    supabase = get_client()
    resultado = supabase.table("notas_fiscais").select("*, clientes(nome, cpf_cnpj, uf)").eq("usuario_id", usuario["id"]).order("criado_em", desc=True).execute()
    return resultado.data


@router.get("/{nota_id}")
def buscar_nota(nota_id: str, usuario=Depends(validar_token)):
    supabase = get_client()
    nota = supabase.table("notas_fiscais").select("*").eq("id", nota_id).eq("usuario_id", usuario["id"]).single().execute()
    if not nota.data:
        raise HTTPException(status_code=404, detail="Nota não encontrada")
    itens = supabase.table("itens_nota").select("*, produtos(nome, ncm)").eq("nota_id", nota_id).execute()
    return {**nota.data, "itens": itens.data}