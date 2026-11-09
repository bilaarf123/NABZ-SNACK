import sys
path = 'd:/AplikasiSkripsi_29_05_2026/templates/base.html'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
new_lines = []
skip = False
for line in lines:
    if 'class="navbar-nav ms-auto align-items-lg-center"' in line:
        line = line.replace('ms-auto', 'me-auto ms-lg-4')
    if '<!-- Demo Quick Access Panel -->' in line:
        skip = True
    if skip and '{% block extra_js %}{% endblock %}' in line:
        skip = False
        new_lines.append(line)
        continue
    if not skip:
        new_lines.append(line)
with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
