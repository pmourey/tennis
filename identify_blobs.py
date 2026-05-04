import subprocess

hashes = ['84b3abfc', '2e54cd15', 'd65f61bf', 'b4b60598', 'b6175ae9', '43d823a8', '9bffdbf5', '51df65d7']
for h in hashes:
    result = subprocess.run(['git', 'cat-file', '-p', h], capture_output=True)
    text = result.stdout.decode('utf-8', errors='replace')
    lines = text.split('\n')
    print(f"=== {h} ===")
    # Print first block or title-like line
    for i, line in enumerate(lines[:200]):
        if 'block ' in line or 'extends' in line or '<title' in line:
            print(f"  Line {i}: {line[:100]}")
            break
    # Print unique content toward start
    for line in lines[10:20]:
        if line.strip():
            print(f"  {line[:100]}")
    print()


