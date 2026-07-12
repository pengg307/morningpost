import subprocess, sys, os

# Use the project venv
venv_python = r"C:\Users\Pactera\projects\.venv\Scripts\python.exe"
if not os.path.exists(venv_python):
    # fallback: create one
    print("Project venv not found, using system python with --break-system-packages")
    venv_python = sys.executable
    cmd = [sys.executable, "-m", "pip", "install", "--break-system-packages", "crewai", "langgraph"]
else:
    print(f"Using project venv: {venv_python}")
    cmd = [venv_python, "-m", "pip", "install", "crewai", "langgraph"]

print(f"Running: {' '.join(cmd[:5])}...")
result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
print("STDOUT (last 3000 chars):")
out = result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout
print(out)
print("\nSTDERR (last 1000 chars):")
err = result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr
print(err)
print(f"\nReturn code: {result.returncode}")
