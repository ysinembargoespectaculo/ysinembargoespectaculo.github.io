#!/usr/bin/env python3
"""
Genera el contenido "visible para buscadores e IA" a partir de la hoja de bolos:
  - Lista estática de actuaciones dentro de index.html (los rastreadores de IA no ejecutan JavaScript)
  - Datos estructurados JSON-LD (grupo + web + eventos) en el <head>
  - llms.txt con las próximas fechas
  - sitemap.xml con la fecha de última modificación
Lo ejecuta la GitHub Action .github/workflows/seo.yml (a diario y en cada push).
"""
import csv, html, io, json, re, sys, unicodedata, urllib.request
from datetime import date, datetime
from zoneinfo import ZoneInfo
MADRID = ZoneInfo("Europe/Madrid")

CSV_URL = ("https://docs.google.com/spreadsheets/d/e/2PACX-1vRVprKQR-zJj25Yd8wVg5yiUwLYxzHjYpw3egpI74FU79BUV8lXkdeiF6K0yVsKvEOJ3Drlb61b7VO1"
           "/pub?gid=0&single=true&output=csv")
WEB = "https://ysinembargoespectaculo.com"
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
MESES_LARGOS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                "septiembre", "octubre", "noviembre", "diciembre"]
MAX_PASADOS = 10
HOY = date.today()


def norm(t):
    t = unicodedata.normalize("NFD", (t or "").strip().lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def parse_fecha(t):
    t = (t or "").strip()
    m = re.match(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})$", t)
    if m:
        y = int(m[3]); y += 2000 if y < 100 else 0
        return date(y, int(m[2]), int(m[1]))
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", t)
    return date(int(m[1]), int(m[2]), int(m[3])) if m else None


def parse_hora(t):
    m = re.match(r"^(\d{1,2})[:.](\d{2})", (t or "").strip())
    return f"{int(m[1]):02d}:{m[2]}" if m else ""


def leer_bolos():
    with urllib.request.urlopen(CSV_URL + "&t=0", timeout=30) as r:
        texto = r.read().decode("utf-8")
    filas = [f for f in csv.reader(io.StringIO(texto)) if any(c.strip() for c in f)]
    if not filas:
        raise RuntimeError("hoja vacía")
    cab = [norm(c) for c in filas.pop(0)]
    get = lambda f, n: (f[cab.index(n)].strip() if n in cab and cab.index(n) < len(f) else "")
    bolos = []
    for f in filas:
        b = {k: get(f, k) for k in ("hora", "lugar", "localidad", "notas", "enlace", "telefono", "cartel")}
        b["fecha"] = parse_fecha(get(f, "fecha"))
        if b["fecha"] and b["lugar"] and norm(get(f, "publicar")) not in ("no", "n", "false", "0"):
            bolos.append(b)
    return bolos


def e(t):
    return html.escape(t or "", quote=True)


def item_html(b, pasado):
    d = b["fecha"]
    fecha = f"{d.day} {MESES[d.month - 1]} {d.year}"
    hora = parse_hora(b["hora"])
    lugar = e(b["lugar"]) + (" · " + e(b["localidad"]) if b["localidad"] else "")
    if not pasado and (b["notas"] or b["telefono"]):
        extra = [e(b["notas"])] if b["notas"] else []
        if b["telefono"]:
            extra.append(f'<a href="tel:{re.sub(r"[^0-9+]", "", b["telefono"])}">{e(b["telefono"])}</a>')
        lugar += f'<span class="actuacion-notas">{" · ".join(extra)}</span>'
    boton = ""
    if not pasado and re.match(r"^https?://", b["enlace"], re.I):
        boton = f'<a class="actuacion-link" href="{e(b["enlace"])}" target="_blank" rel="noopener">Entradas / info</a>'
    return (f'<div class="actuacion-item"><span class="actuacion-fecha"><time datetime="{d.isoformat()}">{fecha}</time></span>'
            f'<span class="actuacion-lugar">{lugar}</span><span class="actuacion-botones">{boton}</span>'
            f'<span class="actuacion-hora">{hora + " h" if hora else ""}</span></div>')


def evento_jsonld(b):
    d = b["fecha"]
    hora = parse_hora(b["hora"])
    ev = {
        "@type": "TheaterEvent",
        "name": f"Y sin embargo... Homenaje a Sabina — {b['lugar']}" + (f" ({b['localidad']})" if b["localidad"] else ""),
        "startDate": (datetime.combine(d, datetime.strptime(hora, "%H:%M").time(), MADRID).isoformat()
                      if hora else d.isoformat()),
        "eventStatus": "https://schema.org/EventScheduled",
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "location": {"@type": "Place", "name": b["lugar"],
                     "address": {"@type": "PostalAddress", "addressLocality": b["localidad"] or b["lugar"],
                                 "addressCountry": "ES"}},
        "performer": {"@id": WEB + "/#grupo"},
        "organizer": {"@id": WEB + "/#grupo"},
        "image": WEB + "/assets/img/banner-rrss.jpg",
        "description": "Espectáculo de teatro musical que rinde homenaje a las canciones de Joaquín Sabina."
                       + (" " + b["notas"] if b["notas"] else ""),
    }
    if re.match(r"^https?://", b["enlace"], re.I):
        ev["offers"] = {"@type": "Offer", "url": b["enlace"], "availability": "https://schema.org/InStock"}
        ev["url"] = b["enlace"]
    else:
        ev["url"] = WEB + "/#carteles"
    return ev


def jsonld(proximos):
    grafo = [
        {
            "@type": ["PerformingGroup", "TheaterGroup"],
            "@id": WEB + "/#grupo",
            "name": "Y sin embargo... Homenaje a Sabina",
            "alternateName": ["Y sin embargo", "Y sin embargo Sabina", "Homenaje a Sabina Y sin embargo"],
            "url": WEB,
            "logo": WEB + "/assets/img/logo-web.png",
            "image": WEB + "/assets/img/banner-rrss.jpg",
            "description": ("Espectáculo de teatro musical que rinde homenaje a Joaquín Sabina: un viaje íntimo por su vida, "
                            "su poesía y sus canciones, donde música y teatro se entrelazan sin imitaciones. "
                            "Nueve artistas en escena con músicos en directo y narrador."),
            "genre": ["Teatro musical", "Homenaje", "Canción de autor"],
            "email": "ysinembargoespectaculo@gmail.com",
            "telephone": "+34 699 698 457",
            "areaServed": "ES",
            "knowsAbout": "Joaquín Sabina",
            "sameAs": [
                "https://www.instagram.com/ysinembargoespectaculo/",
                "https://www.facebook.com/ysinembargoespectaculo",
                "https://www.youtube.com/@ysinembargoespectaculo",
                "https://www.tiktok.com/@ysinembargoespectaculo",
            ],
            "contactPoint": {"@type": "ContactPoint", "contactType": "Contratación y reservas",
                             "email": "ysinembargoespectaculo@gmail.com", "telephone": "+34 699 698 457",
                             "availableLanguage": "es"},
        },
        {
            "@type": "WebSite", "@id": WEB + "/#web", "url": WEB, "inLanguage": "es-ES",
            "name": "Y sin embargo... Homenaje a Sabina", "publisher": {"@id": WEB + "/#grupo"},
        },
        {
            "@type": "FAQPage", "@id": WEB + "/#faq",
            "mainEntity": [
                {"@type": "Question", "name": "¿Qué es «Y sin embargo... Homenaje a Sabina»?",
                 "acceptedAnswer": {"@type": "Answer", "text":
                    "Un espectáculo de teatro musical en homenaje a Joaquín Sabina: versiones de sus canciones, poemas e "
                    "historias contadas y cantadas en directo, sin imitaciones ni parecidos."}},
                {"@type": "Question", "name": "¿Es un tributo a Sabina con imitador?",
                 "acceptedAnswer": {"@type": "Answer", "text":
                    "No. Es un homenaje: no hay imitaciones del artista, sino versiones propias de sus canciones "
                    "unidas por textos y poemas, con músicos en directo y narrador."}},
                {"@type": "Question", "name": "¿Cómo se contrata el espectáculo para un teatro, festival o ayuntamiento?",
                 "acceptedAnswer": {"@type": "Answer", "text":
                    "Escribiendo a ysinembargoespectaculo@gmail.com o por WhatsApp al +34 699 698 457. "
                    "El dossier está en " + WEB + "/assets/docs/dossier_ysinembargo.pdf"}},
                {"@type": "Question", "name": "¿Dónde y cuándo se puede ver?",
                 "acceptedAnswer": {"@type": "Answer", "text":
                    "Las próximas fechas están publicadas en " + WEB + "/#carteles"}},
            ],
        },
    ]
    grafo += [evento_jsonld(b) for b in proximos]
    datos = {"@context": "https://schema.org", "@graph": grafo}
    return '<script type="application/ld+json">\n' + json.dumps(datos, ensure_ascii=False, indent=2) + "\n</script>"


def reemplazar(texto, marca, nuevo):
    patron = re.compile(rf"(<!-- {marca}:INICIO -->).*?(<!-- {marca}:FIN -->)", re.S)
    if not patron.search(texto):
        sys.exit(f"No encuentro las marcas {marca} en index.html")
    return patron.sub(lambda m: m[1] + "\n" + nuevo + "\n" + m[2], texto)


def fecha_larga(b):
    d = b["fecha"]
    h = parse_hora(b["hora"])
    return f"{d.day} de {MESES_LARGOS[d.month - 1]} de {d.year}" + (f", {h} h" if h else "")


def main():
    bolos = leer_bolos()
    proximos = sorted([b for b in bolos if b["fecha"] >= HOY], key=lambda b: b["fecha"])
    pasados = sorted([b for b in bolos if b["fecha"] < HOY], key=lambda b: b["fecha"], reverse=True)[:MAX_PASADOS]

    idx = open("index.html", encoding="utf-8").read()
    idx_orig = idx
    lista = "".join(item_html(b, False) for b in proximos) or (
        '<p class="bolos-mensaje">Próximas fechas muy pronto. ¿Quieres el espectáculo en tu ciudad o tu evento? '
        '<a href="#contacto">Contacta con nosotros</a>.</p>')
    idx = reemplazar(idx, "BOLOS", lista)
    idx = reemplazar(idx, "BOLOS-PASADOS", "".join(item_html(b, True) for b in pasados))
    idx = reemplazar(idx, "JSONLD", jsonld(proximos))
    open("index.html", "w", encoding="utf-8").write(idx)

    llms = open("llms.txt", encoding="utf-8").read()
    llms_orig = llms
    fechas = "\n".join(f"- {fecha_larga(b)} — {b['lugar']}" + (f" ({b['localidad']})" if b["localidad"] else "")
                       + (f". {b['notas']}" if b["notas"] else "") for b in proximos) \
        or "- Próximas fechas por anunciar. Contratación: ysinembargoespectaculo@gmail.com"
    llms = re.sub(r"(<!-- FECHAS:INICIO -->).*?(<!-- FECHAS:FIN -->)",
                  lambda m: m[1] + "\n" + fechas + "\n" + m[2], llms, flags=re.S)
    open("llms.txt", "w", encoding="utf-8").write(llms)

    if idx == idx_orig and llms == llms_orig:
        print("Sin cambios"); return
    sm = open("sitemap.xml", encoding="utf-8").read()
    sm = re.sub(r"<lastmod>[^<]*</lastmod>", f"<lastmod>{HOY.isoformat()}</lastmod>", sm, count=1)
    open("sitemap.xml", "w", encoding="utf-8").write(sm)
    print(f"OK: {len(proximos)} próximas, {len(pasados)} pasadas")


if __name__ == "__main__":
    main()
