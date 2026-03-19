import sys
with open('test_out.txt', 'r', encoding='utf-16le') as f:
    content = f.read()

start = content.find('Upload PDF Response: ')
if start != -1:
    response = content[start + 21:].split('\n')[0]
    with open('error_utf8.txt', 'w', encoding='utf-8') as out:
        out.write(response)
