#!/usr/bin/env python3
"""Inline web/patchcore.js + web/patchdata.js and the write-up (releases/MD3SatMouse.md) into
web/patcher.src.html -> build/MD3SatPaddlePatcher.html, a standalone page that opens from disk."""
import os
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
s = open(os.path.join(R, 'web', 'patcher.src.html')).read()
core = open(os.path.join(R, 'web', 'patchcore.js')).read().replace('if (typeof module !== \'undefined\') module.exports = PC;', '')
data = open(os.path.join(R, 'web', 'patchdata.js')).read().split('\nif (typeof module')[0]
assert '</script' not in core + data
import markdown, re as _re
md = open(os.path.join(R, 'releases', 'MD3SatMouse.md')).read()
md = _re.sub(r'^# .*\n+', '', md, count=1)            # the page header already names it
doc = markdown.markdown(md, extensions=['tables', 'fenced_code'])
doc = doc.replace('<table>', '<div class="tw"><table>').replace('</table>', '</table></div>')
s = s.replace('/*DOC*/', doc)
s = s.replace('/*CORE*/', core).replace('/*DATA*/', data)
import json, re
P = json.loads(re.search(r'var PATCH = (.*);', data).group(1))
s = s.replace('9800971B', '%08X' % P['patchedCrc'])
HEAD = '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n<style>:root{color-scheme:light}body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>\n</head>\n<body>\n'
s = HEAD + s + '</body>\n</html>\n'
open(os.path.join(R, 'build', 'MD3SatPaddlePatcher.html'), 'w').write(s)
print('patcher', len(s), 'bytes')
