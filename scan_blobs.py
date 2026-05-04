import subprocess, os

objects_dir = '.git/objects'
html_blobs = []

for dirname in os.listdir(objects_dir):
    dirpath = os.path.join(objects_dir, dirname)
    if len(dirname) == 2 and os.path.isdir(dirpath):
        for fname in os.listdir(dirpath):
            full_hash = dirname + fname
            result = subprocess.run(['git', 'cat-file', '-t', full_hash], capture_output=True, text=True)
            if result.stdout.strip() == 'blob':
                size_result = subprocess.run(['git', 'cat-file', '-s', full_hash], capture_output=True, text=True)
                size = int(size_result.stdout.strip())
                if size > 500:
                    content = subprocess.run(['git', 'cat-file', '-p', full_hash], capture_output=True)
                    try:
                        text = content.stdout[:500].decode('utf-8', errors='replace')
                        if '{%' in text or '<!DOCTYPE' in text or '<html' in text:
                            first_line = text.split('\n')[0]
                            html_blobs.append((size, full_hash, first_line))
                    except Exception:
                        pass

html_blobs.sort(reverse=True)
for size, h, line in html_blobs:
    print(f"{size:8d}  {h}  {line[:80]}")


