# test_smtp.py
import socket
import smtplib

def test_connection():
    print("Testing SMTP connection...")
    try:
        # Test DNS resolution
        print("1. Resolving smtp.gmail.com...")
        ip = socket.gethostbyname('smtp.gmail.com')
        print(f"   Resolved to: {ip}")
        
        # Test socket connection
        print("2. Testing socket connection on port 587...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex(('smtp.gmail.com', 587))
        sock.close()
        
        if result == 0:
            print("   ✅ Port 587 is OPEN")
        else:
            print(f"   ❌ Port 587 is BLOCKED (Error: {result})")
            
        # Try SMTP connection
        print("3. Testing SMTP connection...")
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
        server.ehlo()
        server.starttls()
        server.ehlo()
        print("   ✅ SMTP connection successful!")
        server.quit()
        
    except socket.gaierror:
        print("   ❌ Cannot resolve smtp.gmail.com - DNS issue")
    except socket.timeout:
        print("   ❌ Connection timeout - Firewall might be blocking")
    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == '__main__':
    test_connection()