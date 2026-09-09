from fastapi import FastAPI, HTTPException, Response


app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "healthy"}