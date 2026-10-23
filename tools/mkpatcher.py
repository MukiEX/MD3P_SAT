#!/usr/bin/env python3
"""Inline web/patchcore.js + web/patchdata.js and the write-up (docs/TECHNICAL.md) into
web/patcher.tpl.html -> build/MD3_SAT_PADDLE.html, a standalone page that opens from disk."""
import os
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
s = open(os.path.join(R, 'web', 'patcher.tpl.html')).read()
core = open(os.path.join(R, 'web', 'patchcore.js')).read().replace('if (typeof module !== \'undefined\') module.exports = PC;', '')
data = open(os.path.join(R, 'web', 'patchdata.js')).read().split('\nif (typeof module')[0]
assert '</script' not in core + data
import markdown, re as _re
md = open(os.path.join(R, 'docs', 'TECHNICAL.md')).read()
md = _re.sub(r'^# .*\n+', '', md, count=1)            # the page header already names it
doc = markdown.markdown(md, extensions=['tables', 'fenced_code'])
doc = doc.replace('<table>', '<div class="tw"><table>').replace('</table>', '</table></div>')
import base64 as _b64                                  # images in the write-up go inline
for _m in set(_re.findall(r'src="([\w.-]+\.svg)"', doc)):
    _d = _b64.b64encode(open(os.path.join(R, 'docs', _m), 'rb').read()).decode()
    doc = doc.replace('src="%s"' % _m, 'src="data:image/svg+xml;base64,%s" style="width:100%%;height:auto"' % _d)
s = s.replace('/*DOC*/', doc)
s = s.replace('/*CORE*/', core).replace('/*DATA*/', data)
import json, re
P = json.loads(re.search(r'var PATCH = (.*);', data).group(1))
s = s.replace('9800971B', '%08X' % P['patchedCrc'])
s = s.replace('<span id="nsec">13</span>', '<span id="nsec">%d</span>' % len(P['sectors']))
HEAD = '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n<style>:root{color-scheme:light}body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>\n</head>\n<body>\n'
s = HEAD + s + '</body>\n</html>\n'
open(os.path.join(R, 'build', 'MD3_SAT_PADDLE.html'), 'w').write(s)
print('patcher', len(s), 'bytes')
