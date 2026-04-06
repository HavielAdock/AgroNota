from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.routers import clientes, produtos, notas, certificados
from app.models import LoginInput, UsuarioCreate
from app import auth

load_dotenv()

app = FastAPI(
    title="AgroNota API",
    description="Backend para emissão de NF-e para produtores rurais",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://agronota.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(clientes.router,     prefix="/clientes",     tags=["Clientes"])
app.include_router(produtos.router,     prefix="/produtos",     tags=["Produtos"])
app.include_router(notas.router,        prefix="/notas",        tags=["Notas Fiscais"])
app.include_router(certificados.router, prefix="/certificados", tags=["Certificados"])


@app.get("/")
def raiz():
    return {"status": "AgroNota API online"}


@app.get("/health")
def health_check():
    return {"status": "ok", "versao": "1.0.0"}


@app.post("/auth/login", tags=["Auth"])
def login(dados: LoginInput):
    return auth.login(dados.email, dados.senha)


@app.post("/auth/registrar", tags=["Auth"])
def registrar(dados: UsuarioCreate):
    return auth.registrar(dados.model_dump())