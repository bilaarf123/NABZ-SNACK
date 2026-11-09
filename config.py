import os
import socket

def check_mysql_port(host, port):
    try:
        # Coba koneksi socket singkat untuk mengecek ketersediaan port MySQL
        s = socket.create_connection((host, port), timeout=0.5)
        s.close()
        return True
    except Exception:
        return False

class Config:
    # Menggunakan kunci rahasia default untuk pengembangan lokal
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'kunci-rahasia-pedaspol-super-pedas-12345'
    
    # =============================================
    # Konfigurasi MySQL (XAMPP / phpMyAdmin)
    # Host   : localhost / 127.0.0.1
    # User   : root (default XAMPP, tanpa password)
    # DB     : nabzsnack_db
    # =============================================
    MYSQL_HOST     = os.environ.get('MYSQL_HOST', '127.0.0.1')
    MYSQL_USER     = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_DB       = os.environ.get('MYSQL_DB', 'nabzsnack_db')
    MYSQL_PORT     = int(os.environ.get('MYSQL_PORT', 3306))

    if check_mysql_port(MYSQL_HOST, MYSQL_PORT):
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
            f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"
        )
        print("Menggunakan koneksi database MySQL.")
    else:
        # Fallback ke SQLite database lokal (menggunakan path absolut agar seed.py dan app.py sinkron)
        basedir = os.path.abspath(os.path.dirname(__file__))
        db_path = os.path.join(basedir, 'instance', 'database.db')
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + db_path
        print(f"MySQL tidak terdeteksi. Menggunakan koneksi database SQLite lokal ({db_path}).")
    
    # Menonaktifkan tracking modifikasi untuk menghemat memori
    SQLALCHEMY_TRACK_MODIFICATIONS = False
