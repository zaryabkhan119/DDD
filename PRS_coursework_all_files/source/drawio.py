"""Export every figure as an editable draw.io (diagrams.net) file.

One .drawio file with one page per figure. Entities/tables/collections are
draw.io ER table shapes; relationships use draw.io's native Crow's Foot
arrow ends. Positions come from a Graphviz layout so the pages open tidy.
"""
import html
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from model import TABLES, RELATIONSHIPS, DOMAIN_COLOURS, conceptual_entities
from diagrams import DOC_SHAPES, VIEWS, COLLECTIONS

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "../build")
ER = {"1": "ERmandOne", "01": "ERzeroToOne", "1N": "ERoneToMany", "0N": "ERzeroToMany"}
ROW_H, HEAD_H, CHAR_W = 20, 26, 7.2
ENC = "#B00020"


class Page:
    def __init__(self, name):
        self.name = name
        self.cells = []
        self.n = 0
        self.nodes = {}   # name -> (w, h)
        self.edges = []   # (src, dst, label) for layout

    def nid(self):
        self.n += 1
        return f"c{self.n}"

    def table(self, name, rows, domain, collapsed=False):
        """rows: list of (html_text, key) ; returns dict key->cell id"""
        fill, line = DOMAIN_COLOURS[domain]
        width = max([len(name) * 8.5] + [len(html.unescape(_strip(t))) * CHAR_W for t, _ in rows]) + 24
        height = HEAD_H + ROW_H * len(rows)
        cid = self.nid()
        style = (f"swimlane;shape=swimlane;fontStyle=1;childLayout=stackLayout;horizontal=1;startSize={HEAD_H};horizontalStack=0;"
                 f"resizeParent=1;resizeParentMax=0;collapsible=0;marginBottom=0;html=1;fontSize=12;"
                 f"fillColor={line};fontColor=#FFFFFF;strokeColor={line};swimlaneFillColor={fill};rounded=0;")
        if collapsed:
            style += "dashed=1;fillColor=#F4F4F4;fontColor=" + line + ";swimlaneFillColor=#F4F4F4;"
        self.cells.append(dict(id=cid, value=name, style=style, vertex="1", parent="1", geo=[0, 0, width, height]))
        ids = {}
        for i, (text, key) in enumerate(rows):
            rid = self.nid()
            self.cells.append(dict(id=rid, value=text, vertex="1", parent=cid,
                                   style="text;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;"
                                         "spacingLeft=6;spacingRight=4;overflow=hidden;rotatable=0;fontColor=#000000;"
                                         "points=[[0,0.5],[1,0.5]];portConstraint=eastwest;html=1;fontSize=11;",
                                   geo=[0, HEAD_H + i * ROW_H, width, ROW_H]))
            ids[key] = rid
        self.nodes[name] = (width, height, cid)
        return ids

    def edge(self, src_cell, dst_cell, start, end, label="", dashed=False, color="#555555", layout=None):
        style = (f"edgeStyle=entityRelationEdgeStyle;html=1;fontSize=10;startArrow={start};endArrow={end};"
                 f"startFill=0;endFill=0;strokeColor={color};fontColor=#333333;endSize=10;startSize=10;")
        if dashed:
            style += "dashed=1;"
        self.cells.append(dict(id=self.nid(), value=label, style=style, edge="1", parent="1",
                               source=src_cell, target=dst_cell))
        if layout:
            self.edges.append((*layout, label))

    def note(self, text, w=340):
        cid = self.nid()
        h = 22 + 18 * text.count("<br>")
        self.cells.append(dict(id=cid, value=text, vertex="1", parent="1",
                               style="text;html=1;align=left;verticalAlign=top;whiteSpace=wrap;strokeColor=#333333;fontColor=#000000;"
                                     "fillColor=#FFFFFF;spacing=6;fontSize=11;", geo=[0, 0, w, h]))
        self.nodes["__legend"] = (w, h, cid)

    def layout(self):
        """Position containers with a Graphviz LR layout."""
        lines = ["digraph G {", "graph [rankdir=LR, nodesep=0.5, ranksep=1.6];", "node [shape=box, fixedsize=true];"]
        for n, (w, h, _c) in self.nodes.items():
            lines.append(f'"{n}" [width={w / 72:.2f}, height={h / 72:.2f}];')
        for a, b, lab in self.edges:
            lines.append(f'"{a}" -> "{b}" [label="{lab}"];')
        lines.append("}")
        js = json.loads(subprocess.run(["dot", "-Tjson"], input="\n".join(lines), capture_output=True,
                                       text=True, check=True).stdout)
        maxy = float(js["bb"].split(",")[3])
        pos = {o["name"]: tuple(map(float, o["pos"].split(","))) for o in js["objects"] if "pos" in o}
        geo = {c["id"]: c for c in self.cells}
        for n, (w, h, cid) in self.nodes.items():
            x, y = pos[n]
            geo[cid]["geo"][0] = round(x - w / 2 + 20)
            geo[cid]["geo"][1] = round(maxy - y - h / 2 + 60)

    def title(self, text):
        self.cells.append(dict(id=self.nid(), value=text, vertex="1", parent="1",
                               style="text;html=1;fontSize=22;fontStyle=1;align=left;fillColor=none;strokeColor=none;fontColor=#1F3A68;", geo=[20, 10, 1200, 36]))

    def xml(self, diagram_el):
        model = ET.SubElement(diagram_el, "mxGraphModel", dx="1600", dy="900", grid="1", gridSize="10",
                              guides="1", tooltips="1", connect="1", arrows="1", fold="1", page="0",
                              pageScale="1", math="0", shadow="0")
        root = ET.SubElement(model, "root")
        ET.SubElement(root, "mxCell", id="0")
        ET.SubElement(root, "mxCell", id="1", parent="0")
        for c in self.cells:
            attrs = {k: v for k, v in c.items() if k not in ("geo",)}
            el = ET.SubElement(root, "mxCell", **attrs)
            if "geo" in c:
                x, y, w, h = c["geo"]
                ET.SubElement(el, "mxGeometry", x=str(x), y=str(y), width=str(round(w)), height=str(round(h)),
                              **{"as": "geometry"})
            else:
                ET.SubElement(el, "mxGeometry", relative="1", **{"as": "geometry"})


def _strip(t):
    import re
    return re.sub("<[^>]+>", "", t)


LEGEND_ER = ("<b>Legend</b><br><u><b>Attribute</b></u> = identifier<br>"
             f"<font color='{ENC}'><b>[E]</b></font> = encrypted sensitive attribute<br>"
             "<font color='#7a4b00'>[S]</font> = sensitive personal data<br>"
             "Crow's Foot ends: ┼┼ exactly one, ┼○ zero or one,<br>┼&lt; one or many, ○&lt; zero or many<br>"
             "Dashed grey = detailed in another view")


def conceptual_page(name, title, subset=None):
    pg = Page(name)
    pg.title(title)
    ents = conceptual_entities()
    rels = RELATIONSHIPS if not subset else [r for r in RELATIONSHIPS if r[0] in subset or r[1] in subset]
    shown = set(ents) if not subset else ({r[0] for r in rels} | {r[1] for r in rels} | set(subset))
    head = {}
    for n, e in ents.items():
        if n not in shown:
            continue
        if subset and n not in subset:
            pg.table(n, [], e["domain"], collapsed=True)
        else:
            rows = []
            for a, pk, enc, sens in e["attrs"]:
                t = html.escape(a)
                if pk:
                    t = f"<u><b>{t}</b></u>"
                if enc:
                    t = f"<font color='{ENC}'><b>{t} [E]</b></font>"
                elif sens:
                    t = f"<font color='#7a4b00'>{t} [S]</font>"
                rows.append((t, a))
            pg.table(n, rows, e["domain"])
        head[n] = pg.nodes[n][2]
    for a, b, ca, cb, lab in rels:
        pg.edge(head[a], head[b], ER[ca], ER[cb], lab, layout=(a, b))
    pg.note(LEGEND_ER)
    pg.layout()
    return pg


def relational_page(name, title, subset=None):
    pg = Page(name)
    pg.title(title)
    shown = set(TABLES)
    if subset:
        shown = set(subset)
        for n in subset:
            shown |= {o["fk"].split(".")[0] for _c, _t, o in TABLES[n]["cols"] if o.get("fk")}
    rowids = {}
    for n, t in TABLES.items():
        if n not in shown:
            continue
        if subset and n not in subset:
            pk = [c for c, _, o in t["cols"] if o.get("pk")]
            ids = pg.table(n, [(f"PK <b><u>{c}</u></b>", c) for c in pk], t["domain"], collapsed=True)
        else:
            rows = []
            for c, typ, o in t["cols"]:
                keys = ",".join(k for k, f in (("PK", "pk"), ("FK", "fk"), ("XR", "xref"), ("UQ", "unique")) if o.get(f))
                nm = f"<b><u>{c}</u></b>" if o.get("pk") else c
                ty = typ + ("" if o.get("null") else " NN")
                if o.get("enc"):
                    ty += f" <font color='{ENC}'><b>AE-{'Det' if o['enc'] == 'DET' else 'Rnd'}</b></font>"
                rows.append((f"<font style='font-size:9px'>{keys}</font>&nbsp;{nm}&nbsp;&nbsp;"
                             f"<font color='#555555'>{html.escape(ty) if 'font' not in ty else ty}</font>", c))
            ids = pg.table(n, rows, t["domain"])
        rowids.update({(n, k): v for k, v in ids.items()})
    for n, t in TABLES.items():
        if n not in shown or (subset and n not in subset):
            continue
        for c, _t, o in t["cols"]:
            if o.get("fk"):
                tt, tc = o["fk"].split(".")
                pg.edge(rowids[(tt, tc)], rowids[(n, c)], "ERzeroToOne" if o.get("null") else "ERmandOne",
                        "ERzeroToMany", layout=(tt, n))
    pg.note("<b>Legend</b><br>PK primary key, FK foreign key, UQ unique, NN NOT NULL<br>"
            "XR cross-store reference to MongoDB (UploadId → VaccinationUpload._id)<br>"
            f"<font color='{ENC}'><b>AE-Det / AE-Rnd</b></font> Always Encrypted (deterministic / randomised)<br>"
            "Lines run from the referenced PK to the FK row<br>Dashed grey = detailed in another view", w=420)
    pg.layout()
    return pg


def document_page():
    pg = Page("Figure 3 Document model")
    pg.title("Figure 3. PRS document logical model (MongoDB)")
    rowids = {}
    for n, fields in DOC_SHAPES.items():
        dom = COLLECTIONS.get(n, {}).get("domain", "vaccination")
        rows = []
        for f, t, note in fields:
            fn = f"<i>{html.escape(f)}</i>" if (f.endswith("[]") or t.startswith("object")) else html.escape(f)
            if "CSFLE" in note:
                fn = f"<font color='{ENC}'><b>{fn} [E]</b></font>"
            rows.append((f"{fn} : <font color='#555555'>{html.escape(t)}</font>"
                         + (f"  <font color='#777777' style='font-size:10px'>{html.escape(note)}</font>" if note else ""),
                         f.split()[0].rstrip("[]")))
        rowids.update({(n, k): v for k, v in pg.table(n, rows, dom).items()})
    sql_rows = [("Person.PRSId", "Person"), ("UserAccount.UserId", "UserAccount"), ("Store.StoreId", "Store"),
                ("GovernmentOfficial.OfficialId", "GovernmentOfficial"),
                ("VaccinationRecord.VaccinationRecordId / UploadId", "VaccinationRecord")]
    rowids.update({("SQL", k): v for k, v in pg.table("MS SQL Server (system of record)", sql_rows, "identity").items()})
    S = "MS SQL Server (system of record)"
    links = [("Person", "VaccinationUpload", "PRSId", "PRSId"), ("UserAccount", "VaccinationUpload", "UploadedByUserId", "UserId"),
             ("VaccinationRecord", "VaccinationUpload", "_id", "UploadId ↔ _id"), ("UserAccount", "AuditLog", "Actor", "UserId"),
             ("Person", "Notification", "PRSId", "PRSId"), ("Store", "Notification", "StoreId", "StoreId"),
             ("GovernmentOfficial", "Announcement", "PublishedBy", "OfficialId")]
    for s, coll, field, lab in links:
        pg.edge(rowids[("SQL", s)], rowids[(coll, field)], "none", "open", lab, dashed=True, color="#3B6FD8", layout=(S, coll))
    G = "GridFS bucket: PRSFiles"
    pg.edge(rowids[("VaccinationUpload", "File")], rowids[(G, "PRSFiles.files")], "none", "open", "File.GridFsId",
            color="#C77700", layout=("VaccinationUpload", G))
    pg.edge(rowids[("Announcement", "Attachments")], rowids[(G, "PRSFiles.files")], "none", "open", "GridFsId",
            color="#1F8A99", layout=("Announcement", G))
    pg.note("<b>Legend</b><br><i>italic</i> = embedded sub-document / array<br>"
            f"<font color='{ENC}'><b>[E]</b></font> = client-side field-level encryption<br>"
            "<font color='#3B6FD8'>dashed blue</font> = reference by shared key to SQL Server<br>"
            "solid = reference to a GridFS file", w=380)
    pg.layout()
    return pg


def main():
    pages = [conceptual_page("Figure 1 Conceptual ERD", "Figure 1. PRS conceptual ER model (Crow's Foot notation)")]
    for k, label, members in VIEWS:
        pages.append(conceptual_page(f"Figure 1{k}", f"Figure 1{k}. Conceptual ER model, detail view: {label}",
                                     [m for m in members if m not in ("UserRole", "RolePermission")]))
    pages.append(relational_page("Figure 2 Relational", "Figure 2. PRS relational logical model (MS SQL Server)"))
    for k, label, members in VIEWS:
        pages.append(relational_page(f"Figure 2{k}", f"Figure 2{k}. Relational model, detail view: {label}",
                                     [m for m in members if m in TABLES]))
    pages.append(document_page())
    mxfile = ET.Element("mxfile", host="app.diagrams.net", type="device")
    for i, pg in enumerate(pages):
        d = ET.SubElement(mxfile, "diagram", id=f"page{i}", name=pg.name)
        pg.xml(d)
    path = OUT / "PRS_diagrams.drawio"
    ET.ElementTree(mxfile).write(path, encoding="utf-8", xml_declaration=False)
    print("wrote", path, len(pages), "pages")


if __name__ == "__main__":
    main()
