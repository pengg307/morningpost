import sys
mods = ['crewai', 'langgraph', 'requests', 'dotenv']
for m in mods:
    try:
        __import__(m)
        print(f'{m}: OK')
    except Exception as e:
        print(f'{m}: MISSING ({e})')
