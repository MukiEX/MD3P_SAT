import sys, os, zipfile, hashlib, io
from playwright.sync_api import sync_playwright
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
page_html = open(os.path.join(R, 'build', 'MD3_SAT_PADDLE.html')).read()
doc = os.path.join(R, 'work', 'ui_test.html')
open(doc, 'w').write('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body>' + page_html + '</body></html>')
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome' if os.path.exists('/opt/pw-browsers/chromium-1194/chrome-linux/chrome') else None)
    pg = b.new_page(accept_downloads=True, viewport={'width': 1200, 'height': 1000})
    logs = []; pg.on('console', lambda m: logs.append(m.text)); pg.on('pageerror', lambda e: logs.append('ERR ' + str(e)))
    pg.goto('file://' + doc)
    pg.screenshot(path=os.path.join(R, 'shots', 'ui_rest.png'), full_page=True)
    for src, opts in sys.argv[1:] and [(a, None) for a in sys.argv[1:]] or []:
        if opts: pass
        pg.set_input_files('#pick', src)
        pg.click('#go')
        pg.wait_for_function("document.getElementById('status').className.includes('ok') || document.getElementById('status').className.includes('err')", timeout=600000)
        print(os.path.basename(src), '->', pg.inner_text('#status'))
        if 'err' in pg.get_attribute('#status', 'class'): continue
        with pg.expect_download() as dl: pg.click('#save')
        out = os.path.join(R, 'work', 'ui_' + os.path.basename(src) + '.zip'); dl.value.save_as(out)
        z = zipfile.ZipFile(out); print(' zip:', [(i.filename, i.file_size) for i in z.infolist()], 'testzip', z.testzip())
        z.extractall(os.path.join(R, 'work', 'ui_out'))
    pg.screenshot(path=os.path.join(R, 'shots', 'ui_done.png'), full_page=True)
    print('\n'.join(logs[:20]))
    b.close()
