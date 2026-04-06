from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime
import re


# ─── AUTENTICAÇÃO ────────────────────────────────────────────

class LoginInput(BaseModel):
    email: str
    senha: str


class TokenOutput(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ─── USUÁRIO ─────────────────────────────────────────────────

class UsuarioCreate(BaseModel):
    email: str
    senha: str
    nome: str
    cpf_cnpj: str
    razao_social: str
    uf: str
    cidade: str
    inscricao_estadual: Optional[str] = None
    regime_tributario: str = "simples_nacional"


class UsuarioOutput(BaseModel):
    id: str
    email: str
    nome: str
    cpf_cnpj: str
    razao_social: str
    uf: str
    cidade: str
    inscricao_estadual: Optional[str] = None
    regime_tributario: str
    modo_interface: str


# ─── CLIENTE ─────────────────────────────────────────────────

class ClienteCreate(BaseModel):
    cpf_cnpj: str
    nome: str
    uf: str
    cidade: str
    inscricao_estadual: Optional[str] = None
    is_contribuinte: bool = False
    email: Optional[str] = None

    @field_validator("cpf_cnpj")
    @classmethod
    def validar_cpf_cnpj(cls, v):
        numeros = re.sub(r"\D", "", v)
        if len(numeros) not in (11, 14):
            raise ValueError("CPF deve ter 11 dígitos ou CNPJ deve ter 14 dígitos")
        return v

    @field_validator("uf")
    @classmethod
    def validar_uf(cls, v):
        ufs = ["AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS",
               "MG","PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC",
               "SP","SE","TO"]
        if v.upper() not in ufs:
            raise ValueError("UF inválida")
        return v.upper()


class ClienteOutput(ClienteCreate):
    id: str
    usuario_id: str
    criado_em: datetime


# ─── PRODUTO ─────────────────────────────────────────────────

class ProdutoCreate(BaseModel):
    nome: str
    ncm: str
    unidade: str
    valor_unitario: Optional[float] = None
    tem_beneficio_fiscal: bool = False

    @field_validator("ncm")
    @classmethod
    def validar_ncm(cls, v):
        numeros = re.sub(r"\D", "", v)
        if len(numeros) != 8:
            raise ValueError("NCM deve ter 8 dígitos")
        return v


class ProdutoOutput(ProdutoCreate):
    id: str
    usuario_id: str
    criado_em: datetime


# ─── EMISSÃO DE NOTA ─────────────────────────────────────────

class EmitirNotaInput(BaseModel):
    cliente_id: str
    produto_id: str
    quantidade: float
    valor_unitario: float

    @field_validator("quantidade", "valor_unitario")
    @classmethod
    def validar_positivo(cls, v):
        if v <= 0:
            raise ValueError("Valor deve ser maior que zero")
        return v


class ItemNotaOutput(BaseModel):
    produto_id: str
    quantidade: float
    valor_unitario: float
    valor_total: float
    icms_aliquota: Optional[float] = None
    icms_valor: Optional[float] = None


class NotaFiscalOutput(BaseModel):
    id: str
    numero: int
    serie: str
    status: str
    cfop: str
    valor_total: float
    valor_icms: Optional[float] = None
    valor_difal: Optional[float] = None
    gnre_necessaria: bool
    gnre_valor: Optional[float] = None
    gnre_recolhida: bool
    ambiente: str
    chave_acesso: Optional[str] = None
    danfe_url: Optional[str] = None
    emitido_em: Optional[datetime] = None
    criado_em: datetime


# ─── CERTIFICADO ─────────────────────────────────────────────

class CertificadoOutput(BaseModel):
    id: str
    titular: Optional[str] = None
    cnpj_certificado: Optional[str] = None
    validade: Optional[datetime] = None
    criado_em: datetime