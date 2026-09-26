"""Record the two-document pipeline demo in real time: ISDA (IS3) -> swap -> contract (CUA). Playwright headless, 1920x1200."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import json, sys, time
from playwright.sync_api import sync_playwright
T1, T2, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
W, H = 1920, 1200
t1 = json.load(open(T1))["text"]; t2 = json.load(open(T2))["text"]
SETUP = """t => { const a = document.querySelector('#dtext'); a.value = t; a.scrollTop = 0; a.style.height = '46px';
  document.documentElement.style.zoom = '1.1'; const g = document.querySelector('.grid'); if (g) { g.style.gridTemplateColumns = '1fr'; g.firstElementChild.style.display = 'none' }
  window.scrollTo(0, 0) }"""
def run(pg, n):
    pg.click("#dgo")
    pg.wait_for_function(f"document.querySelector('#plog').children.length >= {n}", timeout=240000)
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": W, "height": H}, color_scheme="dark", record_video_dir=OUT, record_video_size={"width": W, "height": H})
    ctx.add_init_script("""document.addEventListener('DOMContentLoaded', () => { const s = document.createElement('style');
      s.textContent = 'html{zoom:1.1} .grid{grid-template-columns:1fr!important} .grid>*:first-child{display:none!important} #dtext{height:46px!important}';
      document.head.appendChild(s) })""")
    pg = ctx.new_page(); pg.goto("http://127.0.0.1:8733/"); pg.wait_for_selector("#dtext")
    pg.evaluate(SETUP, t1); time.sleep(2.0)
    run(pg, 1); time.sleep(2.0)
    pg.evaluate("() => { const r = [...document.querySelectorAll('#dres tr')].find(r => r.cells[0] && r.cells[0].innerText.trim() === 'Governing law'); if (r) r.querySelector('details').open = true }")
    time.sleep(3.5)
    pg.evaluate(SETUP, t2); pg.evaluate("() => window.scrollTo(0, 0)"); time.sleep(1.5)
    run(pg, 2); time.sleep(4.5)
    ctx.close(); b.close()
print("recorded")
