
import os
import time
import paramiko
import socket
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

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

class DesktopWatcher(FileSystemEventHandler):
    """Handle file system events on the desktop"""
    def __init__(self):
        self.processed_items = set()
        self.last_modified = {}  # Track last modification times

    def should_process(self, path):
        """Check if item should be processed"""
        name = os.path.basename(path).lower()
        return "important" in name and path not in self.processed_items

    def check_and_upload(self, path):
        """Check and upload item if needed"""
        if self.should_process(path):
            sftp_path = f"/{os.path.basename(path)}"
            if upload_to_sftp(path, sftp_path):
                self.processed_items.add(path)
                if os.path.isfile(path):
                    self.last_modified[path] = os.path.getmtime(path)
            else:
                print(f"Failed to upload {path}")

    def on_created(self, event):
        """Handle new file/folder creation"""
        path = event.src_path
        if self.should_process(path):
            print(f"New item created: {path}")
            time.sleep(1)  # Wait briefly for file to be fully written
            self.check_and_upload(path)

    def on_modified(self, event):
        """Handle file/folder modification"""
        path = event.src_path
        if os.path.isfile(path) and self.should_process(path):
            current_mtime = os.path.getmtime(path)
            last_mtime = self.last_modified.get(path, 0)
            if current_mtime != last_mtime:
                print(f"File modified: {path}")
                self.check_and_upload(path)
                self.last_modified[path] = current_mtime

    def on_moved(self, event):
        """Handle file/folder rename"""
        path = event.dest_path
        if self.should_process(path):
            print(f"Item moved/renamed to: {path}")
            self.check_and_upload(path)

def main():
    print(f"Monitoring desktop: {DESKTOP_DIR}")
    print(f"SFTP server: {SFTP_HOST}:{SFTP_PORT}")
    print(f"Remote base directory: {REMOTE_BASE_DIR}")

    # Initial scan and upload
    watcher = DesktopWatcher()
    for item in os.listdir(DESKTOP_DIR):
        item_path = os.path.join(DESKTOP_DIR, item)
        watcher.check_and_upload(item_path)

    # Start real-time monitoring
    event_handler = watcher
    observer = Observer()
    observer.schedule(event_handler, DESKTOP_DIR, recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(1)  # Keep the script running
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()