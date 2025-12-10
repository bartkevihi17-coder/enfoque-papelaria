from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Aqui você coloca os domínios que vão poder chamar essa API
origins = [
    "https://SEU-APP-LEITOR.netlify.app",      # leitor web
    "https://enfoquepapelaria.meusige.com.br", # SIGE
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# por simplicidade, guardando em memória; depois dá pra trocar por arquivo/DB
BACKUPS = {}  # exemplo: {"enfoque": {...json...}}

@app.post("/api/backup/{empresa}")
async def salvar_backup(empresa: str, payload: dict):
    # validação básica
    if "itens" not in payload:
        raise HTTPException(status_code=400, detail="Campo 'itens' obrigatório.")
    BACKUPS[empresa] = payload
    return {"ok": True}

@app.get("/api/backup/{empresa}")
async def obter_backup(empresa: str):
    if empresa not in BACKUPS:
        raise HTTPException(status_code=404, detail="Nenhum backup para essa empresa.")
    return BACKUPS[empresa]
