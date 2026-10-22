import subprocess
import os
import sys

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
profile_dir = os.path.abspath(r".\auth_profiles\test_profile")
os.makedirs(profile_dir, exist_ok=True)

cmd = [
    chrome_path,
    f"--user-data-dir={profile_dir}",
    "--no-first-run",
    "--no-default-browser-check",
    "https://gemini.google.com/app"
]

print("Launching:", cmd)
proc = subprocess.Popen(cmd)
print("PID:", proc.pid)
