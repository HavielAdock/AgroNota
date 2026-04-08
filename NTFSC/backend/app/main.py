from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from app.routers import clientes, produtos, notas, certificados
from app.models import LoginInput, UsuarioCreate
from app import auth

load_dotenv()

app = FastAPI(title="AgroNota API", version="1.0.0")

@app.options("/{rest_of_path:path}")
async def preflight(rest_of_path: str):
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        }
    )

@app.middleware("http")
async def cors_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response

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