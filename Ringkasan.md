# Ringkasan Proyek SatAnalyze

Berikut adalah ringkasan komprehensif dari proyek **SatAnalyze** berdasarkan struktur direktori dan kode di dalamnya.

## 1. Penjelasan Proyek
**SatAnalyze** adalah sebuah platform (berupa REST API dan *dashboard* interaktif) yang digunakan untuk melakukan analisis citra satelit. Proyek ini mendukung berbagai sensor satelit (seperti Sentinel, Landsat, MODIS, UAV) untuk menghitung *spectral index* (seperti NDVI, NDWI, MNDWI, dll.) secara otomatis. Selain itu, aplikasi ini juga dapat melakukan thresholding untuk klasifikasi tutupan lahan dan menghasilkan perhitungan luas area, serta *output* berupa GeoTIFF dan GeoJSON.

## 2. Tech Stack yang Digunakan
Proyek ini menggunakan berbagai teknologi modern berbasis Python:
* **Backend API**: FastAPI, Uvicorn (sebagai server ASGI).
* **Frontend / Dashboard**: Streamlit.
* **Geospatial & Image Processing**: Rasterio (manipulasi raster), Numpy (komputasi matriks/array), GeoPandas (manipulasi data vektor spasial), dan Scikit-image (pemrosesan citra seperti algoritma *Otsu thresholding*).
* **Containerization**: Docker & Docker Compose (untuk menjalankan seluruh *environment* dengan mudah).

## 3. Struktur Proyek
```text
Bands Analysis/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── analyze.py
│   ├── core/
│   │   └── index_registry.py
│   ├── schemas/
│   │   └── request.py
│   └── services/
│       ├── area_calculator.py
│       └── threshold.py
├── outputs/
├── .dockerignore
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── frontend.py
├── main.py
├── README.md
└── requirements.txt
```

## 4. Penjelasan Setiap Subfolder dan File
* **`main.py`**: Merupakan titik masuk (*entry point*) dari FastAPI. File ini menginisialisasi aplikasi FastAPI, mendaftarkan *router* API, dan memiliki *endpoint* dasar seperti `/health`.
* **`frontend.py`**: Merupakan kode untuk *dashboard* interaktif yang dibangun menggunakan Streamlit. File ini menangani antarmuka pengguna, visualisasi hasil, serta interaksi untuk *upload* data.
* **`requirements.txt`**: Daftar dependensi dan *library* Python yang dibutuhkan untuk menjalankan proyek.
* **`Dockerfile` & `docker-compose.yml`**: Digunakan untuk membungkus (*containerize*) aplikasi sehingga dapat dijalankan dengan mudah dan konsisten di berbagai sistem tanpa harus mengatur dependensi lokal secara manual.
* **`README.md`**: Dokumentasi proyek yang menjelaskan cara instalasi, fitur utama, dan dokumentasi API.
* **`outputs/`**: Folder yang digunakan untuk menyimpan hasil pemrosesan data (seperti file GeoTIFF atau GeoJSON hasil analisis).
* **Folder `app/`**: Folder utama yang berisi logika inti dari backend aplikasi.
    * **`app/api/v1/analyze.py`**: Berisi *route handlers* atau *endpoint* API (seperti `/analyze/upload-bands`) yang bertugas menerima permintaan dari *frontend*, memproses file yang di-*upload*, dan mengembalikan respon.
    * **`app/core/index_registry.py`**: Berisi definisi dan konfigurasi dari *spectral index* yang didukung (misalnya NDVI butuh band NIR dan Red, NDWI butuh Green dan NIR).
    * **`app/schemas/request.py`**: Berisi definisi model menggunakan Pydantic untuk memvalidasi tipe data yang masuk pada *request* API (seperti memastikan metode thresholding atau nama index yang dimasukkan valid).
    * **`app/services/area_calculator.py`**: Modul yang bertugas melakukan perhitungan statistik luasan area (mengubah hitungan piksel menjadi hektar atau kilometer persegi) dan men-generate data spasial vektor (GeoJSON).
    * **`app/services/threshold.py`**: Modul yang berisi strategi dan algoritma pemisahan batas ambang (*thresholding*), seperti menggunakan nilai default literatur, metode otomatis Otsu, perhitungan kuantil, atau input manual.

## 5. Flow Data Input
Alur masuk dan pemrosesan data dalam proyek ini berjalan sebagai berikut:

1. **User Interface (Input Data)**: Pengguna mengakses *dashboard* (melalui Streamlit di `frontend.py`). Pengguna memilih jenis *index* yang ingin dihitung (misalnya NDVI) dan mengunggah file citra satelit (*band*) yang sesuai (contoh: file `.tif` untuk band NIR dan RED).
2. **Pengiriman Data (Request)**: Setelah pengguna menekan tombol analisis, `frontend.py` akan mengirimkan data file citra beserta konfigurasi (*index* dan *threshold method*) melalui HTTP POST request ke *endpoint* API FastAPI (`/analyze/upload-bands`).
3. **Validasi (Backend)**: FastAPI menerima request tersebut. Melalui `app/schemas/request.py`, data request divalidasi. FastAPI juga mengecek `app/core/index_registry.py` untuk memastikan bahwa *band* yang diunggah sesuai dengan kebutuhan perhitungan *index* yang diminta.
4. **Pemrosesan (Service Layer)**:
    * Citra akan dibaca menggunakan `rasterio` dan `numpy`.
    * Matriks numpy digunakan untuk menghitung *spectral index* sesuai rumus (contoh: `(NIR - RED) / (NIR + RED)` untuk NDVI).
    * Modul `app/services/threshold.py` kemudian akan mengklasifikasikan hasil piksel menjadi fitur yang diamati atau tidak (misalnya mana yang tumbuhan dan mana yang bukan) berdasarkan metode *threshold* (seperti algoritma Otsu).
    * Modul `app/services/area_calculator.py` akan menghitung berapa luas total area fitur tersebut berdasarkan ukuran piksel (resolusi spasial citra) dan membuat bentuk format vektornya (GeoJSON/GeoTIFF).
5. **Pengembalian Data (Response)**: API akan mengembalikan file hasil pemrosesan (seperti status berhasil, matriks citra hasil perhitungan, data GeoJSON tutupan lahan, dan statistik luasnya) kembali ke *frontend*.
6. **Visualisasi (Output Display)**: Terakhir, `frontend.py` menerima data tersebut dan menampilkan citra hasil analisis beserta grafik luasan areanya secara visual dan interaktif di layar pengguna. Pengguna juga diberi opsi untuk mengunduh hasil tersebut.
