# API Backup Enfoque

Projeto mínimo para rodar no Render como Web Service em Python.

## Arquivos

- `api_backup.py`: código FastAPI com:
  - `POST /api/backup/from-mobile/enfoque`
  - `GET  /api/backup/from-mobile/enfoque`
- `requirements.txt`: dependências para instalar FastAPI e Uvicorn.

## Start Command no Render

Use este comando como Start Command:

```bash
uvicorn api_backup:app --host 0.0.0.0 --port $PORT
```
