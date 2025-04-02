import os
import time
import paramiko
import socket

# SFTP server credentials
SFTP_HOST = "137.255.67.85"
SFTP_PORT = 22
SFTP_USER = "prosper"
SFTP_PASS = "g3*PleY6"
DESKTOP_DIR = os.path.join(os.path.expanduser("~"), "Desktop")
REMOTE_BASE_DIR = "/DRONE FOOTAGES"

def upload_file_to_sftp(sftp, local_path, remote_path):
    """Upload a single file to SFTP"""
    print(f"Trying to upload file: {local_path} to {remote_path}")
    try:
        sftp.put(local_path, remote_path)
        print(f"Successfully uploaded file: {local_path} to {remote_path}")
        return True
    except Exception as e:
        print(f"File upload error: {e}")
        return False

def upload_directory_to_sftp(sftp, local_dir, remote_dir):
    """Recursively upload a directory to SFTP"""
    print(f"Trying to upload directory: {local_dir} to {remote_dir}")
    try:
        try:
            sftp.stat(remote_dir)
            print(f"Directory {remote_dir} already exists")
        except:
            print(f"Creating remote directory: {remote_dir}")
            sftp.mkdir(remote_dir)
        
        for item in os.listdir(local_dir):
            local_path = os.path.join(local_dir, item)
            remote_path = f"{remote_dir}/{item}"
            
            if os.path.isfile(local_path):
                upload_file_to_sftp(sftp, local_path, remote_path)
            elif os.path.isdir(local_path):
                upload_directory_to_sftp(sftp, local_path, remote_path)
        return True
    except Exception as e:
        print(f"Directory upload error: {e}")
        return False

def upload_to_sftp(local_path, sftp_path):
    """Upload file or directory to SFTP server"""
    print(f"Attempting to upload: {local_path}")
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SFTP_HOST, port=SFTP_PORT, username=SFTP_USER, 
                   password=SFTP_PASS, timeout=10)
        print("Connected to SFTP server")
        
        sftp = ssh.open_sftp()
        
        # Ensure base directory exists
        try:
            sftp.stat(REMOTE_BASE_DIR)
            print(f"Base directory {REMOTE_BASE_DIR} exists")
        except:
            print(f"Creating base directory: {REMOTE_BASE_DIR}")
            sftp.mkdir(REMOTE_BASE_DIR)
        
        remote_full_path = f"{REMOTE_BASE_DIR}{sftp_path}"
        
        if os.path.isfile(local_path):
            success = upload_file_to_sftp(sftp, local_path, remote_full_path)
        elif os.path.isdir(local_path):
            success = upload_directory_to_sftp(sftp, local_path, remote_full_path)
        else:
            print(f"Skipping {local_path}: not a file or directory")
            success = False
            
        sftp.close()
        ssh.close()
        return success
        
    except Exception as e:
        print(f"SFTP connection error: {e}")
        return False

def create_test_file():
    """Create a test file on the desktop if no important items exist"""
    test_file_path = os.path.join(DESKTOP_DIR, "important_test.txt")
    if not os.path.exists(test_file_path):
        try:
            with open(test_file_path, 'w') as f:
                f.write("This is a test file for SFTP upload")
            print(f"Created test file: {test_file_path}")
        except Exception as e:
            print(f"Error creating test file: {e}")

def main():
    processed_items = set()
    print(f"Monitoring desktop: {DESKTOP_DIR}")
    print(f"SFTP server: {SFTP_HOST}:{SFTP_PORT}")
    print(f"Remote base directory: {REMOTE_BASE_DIR}")
    
    while True:
        try:
            print("Scanning desktop...")
            items = [i for i in os.listdir(DESKTOP_DIR) 
                    if "important" in i.lower()]
            
            if not items:
                create_test_file()
                items = [i for i in os.listdir(DESKTOP_DIR) 
                        if "important" in i.lower()]
            
            print(f"Found {len(items)} important items: {items}")
            
            for item in items:
                item_path = os.path.join(DESKTOP_DIR, item)
                if item_path not in processed_items:
                    print(f"New item detected: {item}")
                    sftp_path = f"/{item}"
                    if upload_to_sftp(item_path, sftp_path):
                        processed_items.add(item_path)
                    else:
                        print(f"Failed to upload {item}")
            
            time.sleep(60)
            
        except Exception as e:
            print(f"Main loop error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()