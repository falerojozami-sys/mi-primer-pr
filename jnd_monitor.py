#!/usr/bin/env python3
"""
Monitor de convocatorias de la Junta Nacional de Drogas (gub.uy).

Avisa por mail cuando aparece una convocatoria NUEVA en el listado.
Guarda en seen.json lo que ya vio. La primera corrida solo "siembra" el
estado y no manda nada (si no, te llegarian las 46 de golpe).

Variables de entorno para el mail (todas obligatorias para enviar):
  SMTP_HOST   (ej: smtp.gmail.com)
  SMTP_PORT   (opcional, por defecto 465, SSL)
  SMTP_USER   (tu casilla)
  SMTP_PASS   (contrasena de aplicacion, no la de siempre)
  MAIL_TO     (a donde queres que llegue; puede ser la misma casilla)

Si faltan, imprime el aviso por consola y no falla.

Si la pagina cambia de estructura y el parser no encuentra nada, el script
termina con error a proposito: asi la corrida falla de forma visible en vez
de quedarse callada para siempre.
"""
import json
import os
import re
import smtplib
import sys
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = "https://www.gub.uy"
LIST_URL = BASE + "/junta-nacional-drogas/comunicacion/convocatorias"
# Con las dos primeras paginas (20 items) sobra: lo nuevo aparece arriba.
PAGES = [0, 1]
STATE_FILE = Path(__file__).with_name("seen.json")
SLUG_RE = re.compile(r"/comunicacion/convocatorias/([^/?#]+)/?$")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; jnd-monitor/1.0; uso personal)"}


def fetch(url, params=None):
    r = requests.get(url, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def parse(html):
    """Devuelve {slug: {title, status, url}} a partir del HTML del listado."""
    soup = BeautifulSoup(html, "html.parser")
    items = {}
    for a in soup.find_all("a", href=True):
        m = SLUG_RE.search(a["href"])
        if not m:
            continue
        slug = m.group(1)
        title = a.get_text(" ", strip=True)
        if not title:
            continue
        # El estado ("Vigente" / "No Vigente") esta en el mismo bloque que el link.
        status = "Desconocido"
        node = a
        for _ in range(4):
            node = node.parent
            if node is None:
                break
            if len(node.find_all("a", href=SLUG_RE)) > 1:
                break  # nos pasamos: ya abarca varios items
            text = node.get_text(" ", strip=True)
            if re.search(r"\bNo\s+Vigente\b", text, re.I):
                status = "No Vigente"
                break
            if re.search(r"\bVigente\b", text, re.I):
                status = "Vigente"
                break
        href = a["href"]
        url = href if href.startswith("http") else BASE + href
        items[slug] = {"title": title, "status": status, "url": url}
    return items


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return None


def save_state(state):
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def notify(new_items):
    lines = []
    for it in new_items:
        lines.append(f"- {it['title']} ({it['status']})\n  {it['url']}")
    body = "Aparecio algo nuevo en las convocatorias de la JND:\n\n" + "\n\n".join(lines)
    body += f"\n\nListado completo: {LIST_URL}\n"
    subject = (
        f"JND: nueva convocatoria - {new_items[0]['title'][:80]}"
        if len(new_items) == 1
        else f"JND: {len(new_items)} convocatorias nuevas"
    )

    host = os.environ.get("SMTP_HOST")
    user = os.environ.get("SMTP_USER")
    pwd = os.environ.get("SMTP_PASS")
    to = os.environ.get("MAIL_TO")
    if not all([host, user, pwd, to]):
        print("[sin SMTP configurado] Esto es lo que se hubiera enviado:\n")
        print(subject + "\n")
        print(body)
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to
    msg.set_content(body)
    port = int(os.environ.get("SMTP_PORT", "465"))
    with smtplib.SMTP_SSL(host, port, timeout=30) as s:
        s.login(user, pwd)
        s.send_message(msg)
    print(f"Mail enviado a {to}")


def main():
    current = {}
    for p in PAGES:
        html = fetch(LIST_URL, params={"page": p} if p else None)
        current.update(parse(html))

    if not current:
        print("ERROR: el parser no encontro convocatorias. Puede que gub.uy "
              "haya cambiado la estructura de la pagina.", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    state = load_state()

    if state is None:
        state = {s: {**d, "first_seen": now} for s, d in current.items()}
        save_state(state)
        print(f"Primera corrida: guarde {len(state)} convocatorias como base, sin avisar.")
        return

    new_slugs = [s for s in current if s not in state]
    if new_slugs:
        new_items = [current[s] for s in new_slugs]
        notify(new_items)  # si el mail falla, lanza error y NO guardamos: reintenta la proxima
        for s in new_slugs:
            state[s] = {**current[s], "first_seen": now}
    # Mantenemos actualizado el estado de lo ya conocido (solo informativo).
    for s, d in current.items():
        if s in state:
            state[s].update({"title": d["title"], "status": d["status"], "url": d["url"]})
    save_state(state)
    print(f"Listo. {len(new_slugs)} nueva(s). Total conocidas: {len(state)}.")


if __name__ == "__main__":
    main()
