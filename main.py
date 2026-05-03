import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import analyze

# Konfigurasi Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Inisialisasi aplikasi FastAPI
app = FastAPI(title="SatAnalyze Backend API")

# Tambahkan CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Dalam production, sesuaikan dengan domain frontend spesifik
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Daftarkan router yang berisi logika pemrosesan band
app.include_router(analyze.router)

@app.get("/")
def read_root():
    logger.info("Akses ke root endpoint")
    return {"message": "SatAnalyze Backend berjalan dengan lancar!"}

# Tambahkan endpoint health check di sini
@app.get("/health")
def health_check():
    logger.info("Akses ke health check")
    return {"status": "sehat", "message": "API siap memproses data citra satelit"}