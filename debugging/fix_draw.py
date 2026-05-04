filepath = '../blueprints/tournament/templates/tournament/draw.html'
with open(filepath, 'r') as f:
    content = f.read()

marker = '<style>\n/* ═══ BRACKET LAYOUT'
first = content.find(marker)
second = content.find(marker, first + 1)
print(f"First: {first}, Second: {second}")

if first != -1 and second != -1:
    new_content = content[:first] + content[second:]
    with open(filepath, 'w') as f:
        f.write(new_content)
    print("Done! Removed", second - first, "chars")
else:
    print("NOT FOUND")

