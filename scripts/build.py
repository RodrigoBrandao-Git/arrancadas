"""Normaliza passadas.json, remove duplicadas e gera planilha .xlsx + dados compactos para a página."""
import json, re, sys, collections
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

DIR = sys.argv[1]
d = json.load(open(f"{DIR}/passadas.json", encoding="utf-8"))


def categoria(c):
    c = re.sub(r"\s*-\s*\d+\s*Inscritos.*", "", c).strip()
    m = re.match(r"\(\s*([^)]*?)\s*\)\s*(?:(\S+)\s*->\s*)?(.*)", c)
    if not m:
        return c.upper()
    sigla = (m.group(2) or m.group(1)).strip()
    nome = m.group(3).strip().upper()
    return f"{nome} ({sigla})" if nome and nome != sigla.upper() else sigla.upper()


def tipo(s):
    s2 = s.lower()
    if "mata" in s2 or "final" in s2 or "chave" in s2 or "decis" in s2 or "disputa" in s2:
        return "Mata-mata"
    if "classif" in s2:
        return "Classificação"
    return "Treino"


for x in d:
    x["cat"] = categoria(x.get("cat", ""))
    x["nome"] = re.sub(r"\s+", " ", x.get("nome", "")).strip().upper()
    x["modelo"] = (x.get("modelo") or "").strip().upper()
    x["carro"] = x["carro"].strip()
    x["tipo"] = tipo(x["sessao"])
    if x.get("total") and x.get("reacao") is not None:
        x["pista"] = round(x["total"] - x["reacao"], 3)
    x["queimou"] = x.get("q") in ("Q", "F") or x.get("r") == "-"

# remove a mesma passada listada em várias páginas (por número, por tempo, classificação...)
prio = {"Mata-mata": 0, "Classificação": 1, "Treino": 2}
d.sort(key=lambda x: prio[x["tipo"]])
uniq = {}
for x in d:
    k = (x["evento_id"], x["carro"], x.get("reacao"), x.get("p60"), x.get("m100"), x.get("total"))
    if k in uniq:
        y = uniq[k]
        for f, v in x.items():
            if y.get(f) in (None, "") and v not in (None, ""):
                y[f] = v
    else:
        uniq[k] = x
d = list(uniq.values())

# completa categoria vazia com a do mesmo carro no mesmo evento
catcar = {(x["evento_id"], x["carro"]): x["cat"] for x in d if x["cat"]}
for x in d:
    if not x["cat"]:
        x["cat"] = catcar.get((x["evento_id"], x["carro"]), "")

d.sort(key=lambda x: (x["data"], x["evento_id"], x["cat"], x.get("pista") or 99))
print(len(d), "passadas únicas;", len({x["nome"] for x in d}), "pilotos;", len({x["evento_id"] for x in d}), "eventos")

# ---------- planilha ----------
COLS = [("Data", "data"), ("Evento", "evento"), ("Fase", "tipo"), ("Sessão", "sessao"), ("Categoria", "cat"),
        ("Carro nº", "carro"), ("Piloto", "nome"), ("Modelo", "modelo"), ("Bateria", "bat"), ("Hora", "hora"),
        ("Queimou", "queimou"), ("Reação", "reacao"), ("60 pés", "p60"), ("100m", "m100"), ("201m", "m201"),
        ("402m", "m402"), ("Tempo pista", "pista"), ("Pista+Reação", "total"), ("Vel. final", "vel")]
wb = Workbook()
ws = wb.active
ws.title = "Todas as passadas"
ws.append([c for c, _ in COLS])
for x in d:
    ws.append([("Sim" if x[k] else "") if k == "queimou" else x.get(k) for _, k in COLS])
hdr = PatternFill("solid", fgColor="1F2937")
for c in ws[1]:
    c.font, c.fill = Font(bold=True, color="FFFFFF"), hdr
widths = [11, 42, 13, 18, 34, 9, 32, 20, 8, 9, 8, 8, 8, 8, 8, 8, 11, 12, 9]
for i, w in enumerate(widths, 1):
    ws.column_dimensions[get_column_letter(i)].width = w
for col in range(12, 19):
    for c in ws.iter_cols(min_col=col, max_col=col, min_row=2):
        for cell in c:
            cell.number_format = "0.000"
ws.freeze_panes = "A2"
ws.auto_filter.ref = ws.dimensions

# melhor passada válida de cada piloto em cada evento
best = {}
for x in d:
    if x["queimou"] or not x.get("pista"):
        continue
    k = (x["evento_id"], x["nome"], x["cat"])
    if k not in best or x["pista"] < best[k]["pista"]:
        best[k] = x
ws2 = wb.create_sheet("Melhor por piloto-evento")
c2 = [("Data", "data"), ("Evento", "evento"), ("Categoria", "cat"), ("Carro nº", "carro"), ("Piloto", "nome"),
      ("Modelo", "modelo"), ("Reação", "reacao"), ("60 pés", "p60"), ("100m", "m100"), ("201m", "m201"),
      ("402m", "m402"), ("Tempo pista", "pista"), ("Pista+Reação", "total"), ("Vel. final", "vel"), ("Sessão", "sessao")]
ws2.append([c for c, _ in c2])
for x in sorted(best.values(), key=lambda x: (x["data"], x["evento"], x["cat"], x["pista"])):
    ws2.append([x.get(k) for _, k in c2])
for c in ws2[1]:
    c.font, c.fill = Font(bold=True, color="FFFFFF"), hdr
for i, w in enumerate([11, 42, 34, 9, 32, 20, 8, 8, 8, 8, 8, 11, 12, 9, 18], 1):
    ws2.column_dimensions[get_column_letter(i)].width = w
ws2.freeze_panes = "A2"
ws2.auto_filter.ref = ws2.dimensions

ws3 = wb.create_sheet("Eventos")
ws3.append(["Data", "Evento", "Passadas", "Pilotos", "Link"])
ev = collections.defaultdict(list)
for x in d:
    ev[(x["data"], x["evento_id"], x["evento"])].append(x)
for (data, eid, nome), xs in sorted(ev.items()):
    ws3.append([data, nome, len(xs), len({x["nome"] for x in xs}), f"http://www.produpark.com.br/temposOnline/{eid}"])
for c in ws3[1]:
    c.font, c.fill = Font(bold=True, color="FFFFFF"), hdr
for i, w in enumerate([11, 60, 10, 10, 50], 1):
    ws3.column_dimensions[get_column_letter(i)].width = w
wb.save(f"{DIR}/tempos_produpark.xlsx")

# ---------- dados compactos para a página ----------
dic = {k: [] for k in ("evento", "cat", "nome", "modelo", "sessao")}
idx = {k: {} for k in dic}


def ref(k, v):
    if v not in idx[k]:
        idx[k][v] = len(dic[k])
        dic[k].append(v)
    return idx[k][v]


def ms(v):
    return round(v * 1000) if v else 0


evs = {}
rows = []
for x in d:
    evs[x["evento_id"]] = [x["data"], ref("evento", x["evento"])]
    rows.append([x["evento_id"], ref("sessao", x["sessao"]), "TCM".index(x["tipo"][0]), ref("cat", x["cat"]),
                 x["carro"], ref("nome", x["nome"]), ref("modelo", x["modelo"]), 1 if x["queimou"] else 0,
                 ms(x.get("reacao")), ms(x.get("p60")), ms(x.get("m100")), ms(x.get("m201")), ms(x.get("m402")),
                 ms(x.get("pista")), ms(x.get("total")), x.get("vel") or 0, x.get("hora") or "", x.get("bat") or ""])
out = dict(ev=evs, dic=dic, rows=rows)
s = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
open(f"{DIR}/dados.js", "w", encoding="utf-8").write("window.DADOS=" + s + ";")
print("dados.js", len(s) // 1024, "KB")
