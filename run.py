# FILE: run.py
# LOCATION: /run.py
# PURPOSE: Run the application with LAN support

from app import app
import socket

def get_local_ip():
    """Get local IP address for LAN access display"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        try:
            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)
        except:
            return "127.0.0.1"

if __name__ == '__main__':
    local_ip = get_local_ip()
    
    print("\n" + "=" * 60)
    print("🌟 SUBMITA - RUNNING WITH PG8000")
    print("=" * 60)
    print(f"📍 Local Access:    http://localhost:5000")
    print(f"📍 LAN Access:      http://{local_ip}:5000")
    print("=" * 60)
    print("🔑 Login Credentials:")
    print("   Admin:    ADMIN001 / Admin123!")
    print("   Lecturer: LEC001 / Lecturer123!")
    print("   Student:  STU001 / Student123!")
    print("=" * 60)
    print("\n✅ Press CTRL+C to stop the server\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=True)