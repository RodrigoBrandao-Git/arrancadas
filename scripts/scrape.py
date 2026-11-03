"""Baixa todos os tempos do produpark.com.br e salva em passadas.json."""
import html, json, os, re, sys, hashlib, time, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor

BASE = "http://www.produpark.com.br"
OUT = sys.argv[1]
CACHE = os.path.join(OUT, "cache")
os.makedirs(CACHE, exist_ok=True)


def get(url, refresh=False):
    url = urllib.parse.quote(url, safe=":/?&=%")
    fn = os.path.join(CACHE, hashlib.md5(url.encode()).hexdigest())
    if os.path.exists(fn) and not refresh:
        raw = open(fn, "rb").read()
    else:
        for tent in range(6):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                raw = urllib.request.urlopen(req, timeout=40).read()
                if b"mysqli_connect" in raw or b"Erro no comando SQL" in raw[:200]:
                    raise IOError("erro de banco no servidor")
                break
            except Exception as e:
                if tent == 5:
                    print("FALHA", url, e, flush=True)
                    return ""
                time.sleep(3 * (tent + 1))
        open(fn, "wb").write(raw)
    # páginas misturam UTF-8 e cp1252: decodifica UTF-8 e só os bytes inválidos como cp1252
    return raw.decode("utf-8", errors="misto")


def _misto(e):
    return "".join(bytes([b]).decode("cp1252", errors="replace") for b in e.object[e.start:e.end]), e.end


import codecs
codecs.register_error("misto", _misto)


def _byte(ch):
    try:
        return ch.encode("cp1252")
    except UnicodeEncodeError:
        return ch.encode("latin-1") if ord(ch) < 256 else ch.encode("utf-8")


def txt(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def cells(row):
    return [txt(c) for c in re.findall(r"<td[^>]*>(.*?)(?=<td|</tr|$)", row, re.S | re.I)]


def t(v):
    """'06,995' -> 6.995 ; vazio/zerado/59,99x -> None"""
    try:
        x = float(v.replace(",", "."))
    except Exception:
        return None
    return None if x <= 0 or x >= 59.9 else x


def vel(v):
    """velocidade final em km/h; 0 -> None"""
    return int(v) if v.strip().isdigit() and int(v) > 0 else None


def fix(s):
    s = re.sub(r"\s+", " ", s).strip()
    if "Ã" in s:
        try:
            s = b"".join(_byte(ch) for ch in s).decode("utf-8")
        except Exception:
            pass
    return s


COLS = {"Reação": "reacao", "60 Pés": "p60", "100m": "m100", "201m": "m201", "402m": "m402",
        "Pista+R": "total", "Vel.F": "vel", "Carro": "carro", "Nome": "nome", "Modelo": "modelo",
        "Hora": "hora", "Q": "q", "R": "r", "B": "bat", "P": "lado", "Cat": "letra"}
NUM = {"reacao", "p60", "m100", "m201", "m402", "total", "vel"}


def header(c):
    for ini in ("Cat", "B"):
        if ini in c and any(x.startswith("Rea") for x in c):
            h = [fix(x) for x in c[c.index(ini):]]
            m = {}
            for i, nome in enumerate(h):
                k = COLS.get(nome)
                if k and k not in m:
                    m[k] = i
            if "vel" not in m and "V.v201m" in h:
                m["vel"] = h.index("V.v201m")
            return len(h), m
    return None


def linha(c, hd, base):
    n, m = hd
    if len(c) != n:
        return None
    d = dict(base)
    for k, i in m.items():
        d[k] = vel(c[i]) if k == "vel" else t(c[i]) if k in NUM else fix(c[i])
    if d.get("total") is None and d.get("p60") is None:
        return None
    if d.get("total") and d.get("reacao") is not None:
        d["pista"] = round(d["total"] - d["reacao"], 3)
    return d


def parse_html(s, sessao):
    out, cat, comp, hd = [], "", {}, None
    for row in re.split(r"<tr[^>]*>", s, flags=re.I):
        m = re.search(r'class="Categoria"[^>]*>(.*?)</td', row, re.S)
        if m:
            cat = re.sub(r"\s*-\s*\d+\s*Inscritos.*", "", txt(m.group(1)))
        c = cells(row)
        if 'title="Numero do Carro"' in row:
            comp = dict(pos=c[0], carro=c[1], nome=fix(re.sub(r"^\d+-", "", c[2])), modelo=fix(c[3]))
            continue
        if len(c) == 1 and c[0].startswith("("):
            cat = c[0]
            continue
        h = header(c)
        if h:
            hd = h
            continue
        if hd:
            d = linha(c, hd, dict(sessao=sessao, cat=cat, **comp))
            if d:
                out.append(d)
    return out


FASES = {"D": "Mata-mata 16 avos", "O": "Mata-mata Oitavas", "Q": "Mata-mata Quartas",
         "S": "Mata-mata Semifinal", "F": "Mata-mata Final"}


def parse_txt(s):
    out, cat, lay402 = [], "", True
    for l in s.splitlines():
        f = l.split("|")
        if f[0] == "$CATEGORIA":
            cat = fix(f[1])
        elif f[0] == "$DESC_FOT":
            lay402 = "402m" in l
        m = re.match(r"\$([A-Z])_P\d+$", f[0])
        if not m or len(f) < 13 or not f[1].strip() or f[1].strip() == "WO":
            continue
        qr = f[4].strip()
        v = [t(x) for x in f[5:11]]
        vels = [vel(x) for x in f[11].split("-")] if "-" in f[11] else []
        d = dict(sessao=FASES.get(m.group(1), "Mata-mata " + m.group(1)), cat=cat, nome=fix(f[1]),
                 carro=f[2].strip(), modelo=fix(f[3]), q=qr[:1], r=qr[1:2], reacao=t(qr[2:]),
                 p60=v[0], total=v[5], vel=(vels[-1] or vels[0]) if vels else None)
        if lay402:
            d.update(m100=v[1], m201=v[2], m402=v[4])
        else:
            d.update(m100=v[3], m201=v[4])
        if d["total"] is None and d["p60"] is None:
            continue
        if d["total"] and d["reacao"] is not None:
            d["pista"] = round(d["total"] - d["reacao"], 3)
        out.append(d)
    return out


def evento(ev):
    eid, titulo = ev
    s = get(f"{BASE}/controller/listaCategoria.php?id={eid}&local=H", refresh=True)
    links = re.findall(r'data-titulo="([^"]*)" data-url="([^"]*)"', s)
    links = [(a, u) for a, u in links if "semTempo" not in u and "Records" not in u]
    passes, falhas = [], []
    for nome_pag, url in dict.fromkeys(links):
        tipo = url.split("/")[-2]
        sessao = {"Treino": fix(nome_pag), "Class": "Classificação"}.get(tipo, tipo)
        p = get(url)
        r = parse_txt(p) if url.endswith(".txt") else parse_html(p, sessao)
        if not r and len(p) > 3000:
            falhas.append(url)
        passes += r
    return eid, titulo, len(links), passes, falhas


def main():
    s = get(f"{BASE}/controller/controllerCorridas.php?acao=listaFiltro&m=&y=&tipo=U", refresh=True)
    evs = re.findall(r"abreDetalhes\('(\d+)'\).*?abrir\">(.*?)</a>", s)
    evs = [(i, txt(n)) for i, n in evs]
    print(len(evs), "eventos", flush=True)
    dados, todas_falhas = [], []
    with ThreadPoolExecutor(2) as ex:
        for eid, titulo, nl, passes, falhas in ex.map(evento, evs):
            m = re.search(r"(\d\d)/(\d\d)/(\d{4})\s*$", titulo)
            data = f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else ""
            nome_ev = re.sub(r"\s*-\s*\d\d/\d\d/\d{4}\s*$", "", titulo)
            for p in passes:
                p.update(evento_id=int(eid), evento=nome_ev, data=data)
            dados += passes
            todas_falhas += falhas
            print(f"{eid:>4} {data} páginas={nl:3} passadas={len(passes):5} {nome_ev[:60]}", flush=True)
    json.dump(dados, open(os.path.join(OUT, "passadas.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print("TOTAL", len(dados), "passadas; páginas não reconhecidas:", len(todas_falhas))
    for f in todas_falhas:
        print("  ", f)


main()
