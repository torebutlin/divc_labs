"""Export the 3C6 notebook as a handout: HTML, PDF and the lab's printed copy.

    python make_exports.py

writes, next to the notebook:

    3C6_Notebook.html           the notebook as a web page
    3C6_Notebook.pdf            the student handout (A4, page numbers)
    3C6_Notebook_LAB_COPY.pdf   the same, headed 'LAB COPY' on every page

The HTML is nbconvert's lab template without the In [ ]: prompts (the
notebook has no outputs), plus the styling in HANDOUT_CSS. The PDFs are
that page printed by headless Google Chrome over its DevTools protocol,
which lets the print wait for MathJax to typeset the equations and adds
the page-number footer. Needs Chrome and an internet connection (MathJax
comes from a CDN); set CHROME to point at another Chrome or Edge.
"""
import base64
import json
import os
import socket
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

import nbformat
from nbconvert import HTMLExporter
from websockets.sync.client import connect

HERE = Path(__file__).resolve().parent
NOTEBOOK = HERE / '3C6_Notebook.ipynb'
TITLE = '3C6 Digital Vibration Analysis'
CHROME = os.environ.get(
    'CHROME', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
LAB_COPY_HEADER = 'LAB COPY: please leave in South Wing Mechanics Laboratory'
# the lab template's type is large on paper: 0.88 gives about 10 pt body text
PRINT_SCALE = 0.88

HANDOUT_CSS = """
/* 3C6 handout styling (make_exports.py) */
body { max-width: 940px; margin: 0 auto; }
.alert { padding: 10px 14px; margin: 1em 0; border: 1px solid; border-radius: 5px; }
.alert-info { background: #eaf4fb; border-color: #9cc9e4; color: #0b3d5c; }
.alert-danger { background: #fbeeee; border-color: #e3a3a3; color: #6b1515; }
/* the lab-assistant box (the one bordered darkblue): QR code beside the
   text rather than under it, so the box stays short */
.jp-RenderedHTMLCommon div[style*="darkblue"] {
  max-width: 80% !important; display: grid; grid-template-columns: 1fr 130px;
  column-gap: 16px; align-items: center; }
.jp-RenderedHTMLCommon div[style*="darkblue"] > p:has(img) {
  grid-column: 2; grid-row: 1 / span 2; margin: 0; }
.jp-RenderedHTMLCommon div[style*="darkblue"] img { width: 130px; display: block; }
@media print {
  body { max-width: none; }
  .jp-CodeCell, .alert, .jp-RenderedHTMLCommon div[style*="border"],
  .jp-RenderedHTMLCommon img, table, li { break-inside: avoid; }
  /* keep headings (and the rules drawn under section titles) with what follows */
  h1, h2, h3, h4, hr { break-after: avoid; }
  pre { white-space: pre-wrap; }
}
"""

# Chrome draws the header and footer in Times unless told otherwise
SANS = "font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif;"
FOOTER = ('<div style="' + SANS + ' font-size:8px; width:100%; margin:0 14mm; color:#777; '
          'display:flex; justify-content:space-between">'
          '<span>' + TITLE + '</span>'
          '<span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>')
NO_HEADER = '<span></span>'
LAB_HEADER = ('<div style="' + SANS + ' font-size:11px; width:100%; text-align:center; '
              'color:#c00000; font-weight:bold">' + LAB_COPY_HEADER + '</div>')

WAIT_FOR_MATHJAX = """
new Promise(resolve => {
  const done = () => resolve(true);
  if (window.MathJax && MathJax.Hub) MathJax.Hub.Queue(done);
  else setTimeout(done, 1000);
})
"""


def export_html(path):
    nb = nbformat.read(NOTEBOOK, as_version=4)
    nb.metadata['title'] = TITLE
    exporter = HTMLExporter(template_name='lab', exclude_input_prompt=True,
                            exclude_output_prompt=True)
    html, _ = exporter.from_notebook_node(nb)
    html = html.replace('</head>', '<style>' + HANDOUT_CSS + '</style>\n</head>', 1)
    path.write_text(html, encoding='utf-8')
    print('wrote', path.name)


class Chrome:
    """Headless Chrome, driven over the DevTools protocol."""

    def __init__(self):
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0))
            self.port = s.getsockname()[1]
        self.profile = tempfile.TemporaryDirectory()
        self.proc = subprocess.Popen(
            [CHROME, '--headless=new', '--disable-gpu', '--no-first-run',
             '--remote-debugging-port=%d' % self.port,
             '--user-data-dir=' + self.profile.name, 'about:blank'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                urllib.request.urlopen('http://127.0.0.1:%d/json/version' % self.port)
                break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError('Chrome did not start: ' + CHROME)

    def close(self):
        self.proc.terminate()
        self.proc.wait()
        self.profile.cleanup()

    def print_pdf(self, html_path, pdf_path, header):
        req = urllib.request.Request(
            'http://127.0.0.1:%d/json/new?about:blank' % self.port, method='PUT')
        target = json.load(urllib.request.urlopen(req))
        with connect(target['webSocketDebuggerUrl'], max_size=None) as ws:
            ids = iter(range(1, 10**6))

            def call(method, **params):
                msg_id = next(ids)
                ws.send(json.dumps({'id': msg_id, 'method': method, 'params': params}))
                while True:
                    msg = json.loads(ws.recv())
                    if msg.get('id') == msg_id:
                        if 'error' in msg:
                            raise RuntimeError('%s: %s' % (method, msg['error']))
                        return msg['result']

            def wait_for(event):
                while json.loads(ws.recv()).get('method') != event:
                    pass

            call('Page.enable')
            call('Page.navigate', url=html_path.as_uri())
            wait_for('Page.loadEventFired')
            call('Runtime.evaluate', expression=WAIT_FOR_MATHJAX,
                 awaitPromise=True, timeout=30000)
            pdf = call('Page.printToPDF', paperWidth=8.27, paperHeight=11.69,
                       marginTop=0.65, marginBottom=0.65, marginLeft=0.55,
                       marginRight=0.55, scale=PRINT_SCALE, printBackground=True,
                       displayHeaderFooter=True, headerTemplate=header,
                       footerTemplate=FOOTER)
        pdf_path.write_bytes(base64.b64decode(pdf['data']))
        print('wrote', pdf_path.name)


def main():
    html = HERE / '3C6_Notebook.html'
    export_html(html)
    chrome = Chrome()
    try:
        chrome.print_pdf(html, HERE / '3C6_Notebook.pdf', NO_HEADER)
        chrome.print_pdf(html, HERE / '3C6_Notebook_LAB_COPY.pdf', LAB_HEADER)
    finally:
        chrome.close()


if __name__ == '__main__':
    main()
