import sys, os, zipfile, hashlib, io
from playwright.sync_api import sync_playwright
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
doc = os.path.join(R, 'build', 'MD3_SAT_PADDLE.html')   # a complete standalone page
args = [a for a in sys.argv[1:] if not a.startswith('--')]
toggles = [a[2:] for a in sys.argv[1:] if a.startswith('--')]   # e.g. --pure --magnet: click those switches
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome' if os.path.exists('/opt/pw-browsers/chromium-1194/chrome-linux/chrome') else None)
    pg = b.new_page(accept_downloads=True, viewport={'width': 1200, 'height': 1000})
    logs = []; pg.on('console', lambda m: logs.append(m.text)); pg.on('pageerror', lambda e: logs.append('ERR ' + str(e)))
    pg.goto('file://' + doc)
    os.makedirs(os.path.join(R, 'shots'), exist_ok=True)
    pg.evaluate("localStorage.clear()"); pg.reload()
    for t in toggles: pg.click('#%s' % t, force=True)
    pg.screenshot(path=os.path.join(R, 'shots', 'ui_rest.png'), full_page=True)
    for src in args:
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
