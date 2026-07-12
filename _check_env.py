import sys, os
print("Python executable:", sys.executable)
print("Python path:", sys.prefix)
print("Python version:", sys.version)
print()
# Check if crewai is importable
try:
    import crewai
    print("crewai: FOUND")
except ImportError as e:
    print(f"crewai: NOT FOUND - {e}")

try:
    import langgraph
    print("langgraph: FOUND")
except ImportError as e:
    print(f"langgraph: NOT FOUND - {e}")
