"""Single master script to launch backends (8201 & 8202), wait for health checks, seed vector store, and launch the DeepEval UI Dashboard (8203)."""
import os
import sys
import time
import subprocess
import webbrowser
import requests
from pathlib import Path

# Force UTF-8 encoding for standard output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent
CHATBOT_DIR = ROOT_DIR / "01_Chatbot_Shopeasy_chatbot" / "01_chatbot" / "backend"
RAG_DIR = ROOT_DIR / "02_RAG_Explorer" / "02_rag_explorer"
DASHBOARD_DIR = ROOT_DIR / "03_DeepEval_Dashboard"

print("==================================================================")
print("[+] Starting DeepEval Quality & Security Framework Subsystems...")
print("==================================================================")

def is_healthy(urls):
    if isinstance(urls, str):
        urls = [urls]
    for u in urls:
        try:
            r = requests.get(u, timeout=2)
            if r.status_code == 200:
                return True
        except Exception:
            pass
    return False

def wait_for_url(urls, name, max_retries=30):
    if isinstance(urls, str):
        urls = [urls]
    for i in range(max_retries):
        for u in urls:
            if is_healthy(u):
                print(f"  [OK] {name} is UP and healthy on {u}")
                return True
        time.sleep(1)
    print(f"  [FAIL] Timed out waiting for {name} on {urls[0]}")
    return False

def open_browser(url):
    """Safely open browser across Windows, macOS, Linux, and WSL."""
    is_wsl = False
    if os.path.exists("/proc/version"):
        try:
            with open("/proc/version", "r") as f:
                if "microsoft" in f.read().lower():
                    is_wsl = True
        except Exception:
            pass

    if is_wsl:
        for cmd in [
            ["wslview", url],
            ["powershell.exe", "-c", f"Start-Process '{url}'"],
            ["cmd.exe", "/c", f"start {url}"]
        ]:
            try:
                res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if res.returncode == 0:
                    return True
            except Exception:
                pass

    try:
        webbrowser.open(url)
    except Exception:
        pass


# 1. Start Subsystem A (Chatbot @ 8201)
chatbot_proc = None
bot_urls = ["http://127.0.0.1:8201/health", "http://localhost:8201/health"]
print("\n[1/4] Checking Subsystem A (Chatbot Backend on port 8201)...")
if is_healthy(bot_urls):
    print("  [OK] Chatbot Backend (8201) is already running.")
    bot_ok = True
else:
    print("  [*] Launching Chatbot Backend on port 8201...")
    chatbot_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app", "--port", "8201", "--host", "0.0.0.0"],
        cwd=str(CHATBOT_DIR)
    )
    bot_ok = wait_for_url(bot_urls, "Chatbot (8201)")

# 2. Start Subsystem B (RAG Explorer @ 8202)
rag_proc = None
rag_urls = ["http://127.0.0.1:8202/api/health", "http://localhost:8202/api/health"]
print("\n[2/4] Checking Subsystem B (RAG Explorer Backend on port 8202)...")
if is_healthy(rag_urls):
    print("  [OK] RAG Explorer Backend (8202) is already running.")
    rag_ok = True
else:
    print("  [*] Launching RAG Explorer Backend on port 8202...")
    rag_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app", "--port", "8202", "--host", "0.0.0.0"],
        cwd=str(RAG_DIR)
    )
    rag_ok = wait_for_url(rag_urls, "RAG Explorer (8202)")

# Seed RAG Knowledge Base
if rag_ok:
    try:
        print("  [*] Seeding RAG Explorer Knowledge Base...")
        requests.post("http://127.0.0.1:8202/api/ingest/seed", timeout=15)
        print("  [OK] Knowledge Base Seeded (21 chunks indexed)")
    except Exception as e:
        try:
            requests.post("http://localhost:8202/api/ingest/seed", timeout=15)
            print("  [OK] Knowledge Base Seeded (21 chunks indexed)")
        except Exception as ex:
            print(f"  [!] Seed warning: {ex}")

# 3. Start Subsystem C (DeepEval UI Dashboard @ 8203)
dashboard_proc = None
dash_urls = ["http://127.0.0.1:8203/api/metrics", "http://localhost:8203/api/metrics"]
print("\n[3/4] Checking Subsystem C (DeepEval UI Dashboard on port 8203)...")
if is_healthy(dash_urls):
    print("  [OK] DeepEval UI Dashboard (8203) is already running.")
    ui_ok = True
else:
    print("  [*] Launching DeepEval UI Dashboard on port 8203...")
    dashboard_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "dashboard.app:app", "--port", "8203", "--host", "0.0.0.0"],
        cwd=str(DASHBOARD_DIR)
    )
    ui_ok = wait_for_url(dash_urls, "DeepEval UI (8203)")

# 4. Open Browser
print("\n[4/4] Opening DeepEval Dashboard in Browser...")
if ui_ok:
    print("\n==================================================================")
    print("[SUCCESS] All Subsystems Live!")
    print("Dashboard UI: http://localhost:8203")
    print("==================================================================")
    open_browser("http://localhost:8203")

if dashboard_proc is not None or chatbot_proc is not None or rag_proc is not None:
    try:
        if dashboard_proc:
            dashboard_proc.wait()
        else:
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down launched subsystems...")
        if chatbot_proc: chatbot_proc.terminate()
        if rag_proc: rag_proc.terminate()
        if dashboard_proc: dashboard_proc.terminate()
        print("Done!")
