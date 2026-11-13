from fastapi import FastAPI

app = FastAPI(title="Simplifica Conquista")


@app.get("/health")
async def health():
    return {"status": "ok"}
