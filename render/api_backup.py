from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# ------------------ MODELOS ------------------ #

class ItemBackup(BaseModel):
    codigo: str
    quantidade: int

class BackupPayload(BaseModel):
    origem: Optional[str] = ""
    destino: Optional[str] = ""
    responsavel: Optional[str] = ""
    data: Optional[str] = ""   # já vem formatado do app (ex: "10/12/2025 - 15:30")
    itens: List[ItemBackup]

# ------------------ APLICAÇÃO FASTAPI ------------------ #

app = FastAPI(
    title="API Backup Enfoque",
    version="1.0.0",
    description="API simples para receber backup do leitor (iPhone) e entregar para a extensão SIGE."
)

# CORS: se quiser, depois dá pra restringir só pros domínios do seu site/ extensão
origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------ ARMAZENAMENTO EM MEMÓRIA ------------------ #
# Para começar, vamos guardar só em memória (último backup).
# Se o Render reiniciar / hibernar, isso some. Depois podemos trocar por banco.

LAST_MOBILE_BACKUP: dict | None = None
LAST_MOBILE_BACKUP_TS: Optional[datetime] = None


# ------------------ ENDPOINTS ------------------ #

@app.get("/")
def root():
    return {
        "ok": True,
        "service": "API Backup Enfoque",
        "mobile_backup_available": LAST_MOBILE_BACKUP is not None,
        "last_mobile_backup_ts": LAST_MOBILE_BACKUP_TS.isoformat() if LAST_MOBILE_BACKUP_TS else None,
    }


@app.post("/api/backup/from-mobile/enfoque")
def receive_backup_from_mobile(payload: BackupPayload):
    """
    Recebe backup enviado pelo leitor do iPhone.
    Corpo esperado:
    {
      "origem": "...",
      "destino": "...",
      "responsavel": "...",
      "data": "10/12/2025 - 15:30",
      "itens": [
        { "codigo": "789...", "quantidade": 3 },
        ...
      ]
    }
    """
    global LAST_MOBILE_BACKUP, LAST_MOBILE_BACKUP_TS

    if not payload.itens:
        raise HTTPException(status_code=400, detail="Backup sem itens.")

    LAST_MOBILE_BACKUP = payload.dict()
    LAST_MOBILE_BACKUP_TS = datetime.utcnow()

    return {
        "ok": True,
        "message": "Backup do mobile recebido com sucesso.",
        "items_count": len(payload.itens),
    }


@app.get("/api/backup/from-mobile/enfoque")
def get_backup_for_extension():
    """
    Entrega o último backup recebido do mobile para a extensão (Chrome).
    Formato idêntico ao que recebeu.
    """
    if LAST_MOBILE_BACKUP is None:
        raise HTTPException(status_code=404, detail="Nenhum backup vindo do mobile disponível no momento.")

    return LAST_MOBILE_BACKUP
