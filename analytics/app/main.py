from fastapi import FastAPI

app = FastAPI(
    title="Data Story Builder Analytics API",
    version="0.1.0"
)


@app.get("/health")
def health_check():
    return {"status": "healthy"}