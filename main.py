from fastapi import FastAPI
from app.api.v1 import analyze

# Inisialisasi aplikasi FastAPI
app = FastAPI(title="SatAnalyze Backend API")

# Daftarkan router yang berisi logika pemrosesan band
app.include_router(analyze.router)

@app.get("/")
def read_root():
    return {"message": "SatAnalyze Backend berjalan dengan lancar!"}

# Tambahkan endpoint health check di sini
@app.get("/health")
def health_check():
    return {"status": "sehat", "message": "API siap memproses data citra satelit"}