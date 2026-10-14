"""Generate Figures 1-3 (conceptual ERD, relational schema, document model) with Graphviz."""
import html
import subprocess
import sys
from pathlib import Path

from model import (TABLES, COLLECTIONS, RELATIONSHIPS, DOMAIN_COLOURS, DOMAIN_LABELS,
                   conceptual_entities)

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "out")
OUT.mkdir(parents=True, exist_ok=True)

CARD = {"1": "teetee", "01": "teeodot", "1N": "crowtee", "0N": "crowodot"}
FONT = "DejaVu Sans"
ENC_COL = "#B00020"


def esc(s):
    return html.escape(str(s))


def render(dot_src, name, engine="dot"):
    p = OUT / f"{name}.dot"
    p.write_text(dot_src)
    for fmt in ("png", "svg", "pdf"):
        args = [engine, f"-T{fmt}", str(p), "-o", str(OUT / f"{name}.{fmt}")]
        if fmt == "png":
            args.insert(1, "-Gdpi=170")
        subprocess.run(args, check=True)


def legend_rows(extra):
    rows = "".join(f'<TR><TD ALIGN="LEFT">{r}</TD></TR>' for r in extra)
    doms = "".join(
        f'<TR><TD ALIGN="LEFT" BGCOLOR="{DOMAIN_COLOURS[d][1]}"><FONT COLOR="white">{esc(l)}</FONT></TD></TR>'
        for d, l in DOMAIN_LABELS.items())
    return rows + doms


# ---------------------------------------------------------------------------
# Figure 1: conceptual ERD (Crow's Foot)
# ---------------------------------------------------------------------------
def collapsed(name, domain, port=None, extra=""):
    fill, line = DOMAIN_COLOURS[domain]
    p = f' PORT="{port}"' if port else ""
    return (f'"{name}" [label=<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4" STYLE="dashed" '
            f'BGCOLOR="#F4F4F4" COLOR="{line}"><TR><TD{p}><FONT COLOR="{line}"><B>{esc(name)}</B>{extra}</FONT></TD></TR>'
            f'</TABLE>>];')


def conceptual(subset=None, fname="fig1_conceptual_erd",
               title="Figure 1. PRS conceptual ER model (Crow's Foot notation)"):
    ents = conceptual_entities()
    rels = RELATIONSHIPS
    shown = set(ents)
    if subset:
        rels = [r for r in RELATIONSHIPS if r[0] in subset or r[1] in subset]
        shown = {r[0] for r in rels} | {r[1] for r in rels} | set(subset)
    lines = [
        "digraph ERD {",
        f'graph [rankdir=LR, splines=true, overlap=false, nodesep={0.35 if subset else 0.2}, ranksep={0.9 if subset else 0.6}, fontname="{FONT}", '
        f'pad=0.3, newrank=true, labelloc=t, fontsize=26, label="{esc(title)}"];',
        f'node [shape=plain, fontname="{FONT}", fontsize=11];',
        f'edge [fontname="{FONT}", fontsize=10, color="#555555", dir=both, arrowsize=0.9, penwidth=1.1];',
    ]
    assoc = {"FamilyLink": "Person (guardian) + Person (dependant)",
             "StockLevel": "Store + CriticalItem",
             "PurchaseLine": "Purchase + CriticalItem"}
    for name, e in ents.items():
        if name not in shown:
            continue
        if subset and name not in subset:
            lines.append(collapsed(name, e["domain"]))
            continue
        fill, line = DOMAIN_COLOURS[e["domain"]]
        rows = [f'<TR><TD BGCOLOR="{line}" ALIGN="CENTER"><FONT COLOR="white"><B>{esc(name)}</B></FONT></TD></TR>']
        if name in assoc:
            rows.append(f'<TR><TD ALIGN="LEFT"><I><FONT POINT-SIZE="9">associative; identified by {esc(assoc[name])}</FONT></I></TD></TR>')
        for a, pk, enc, sens in e["attrs"]:
            txt = esc(a)
            if pk:
                txt = f"<U><B>{txt}</B></U>"
            if enc:
                txt = f'<FONT COLOR="{ENC_COL}"><B>{txt}  [E]</B></FONT>'
            elif sens:
                txt = f'<FONT COLOR="#7a4b00">{txt}  [S]</FONT>'
            rows.append(f'<TR><TD ALIGN="LEFT">{txt}</TD></TR>')
        lines.append(f'"{name}" [label=<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="3" '
                     f'BGCOLOR="{fill}" COLOR="{line}">{"".join(rows)}</TABLE>>];')
    for a, b, ca, cb, lab in rels:
        lines.append(f'"{a}" -> "{b}" [arrowtail={CARD[ca]}, arrowhead={CARD[cb]}, label="{lab}"];')
    legend = legend_rows([
        "<B>Legend</B>",
        "<U><B>Attribute</B></U> = identifier",
        f'<FONT COLOR="{ENC_COL}"><B>[E]</B></FONT> = encrypted sensitive attribute',
        '<FONT COLOR="#7a4b00">[S]</FONT> = sensitive personal data',
        "─┼┼ exactly one    ─┼○ zero or one",
        "─┼&lt; one or many    ─○&lt; zero or many",
        "Relationship labels read A → B",
    ] + (["Dashed grey box = entity detailed in another view"] if subset else []))
    lines.append(f'Legend [label=<<TABLE BORDER="1" CELLBORDER="0" CELLPADDING="3" BGCOLOR="white">{legend}</TABLE>>];')
    lines.append("}")
    render("\n".join(lines), fname)


# ---------------------------------------------------------------------------
# Figure 2: relational logical model (SQL Server)
# ---------------------------------------------------------------------------
def relational(subset=None, fname="fig2_relational_schema",
               title="Figure 2. PRS relational logical model (MS SQL Server)"):
    shown = set(TABLES)
    if subset:
        shown = set(subset)
        for n in subset:
            for _c, _t, o in TABLES[n]["cols"]:
                if o.get("fk"):
                    shown.add(o["fk"].split(".")[0])
    lines = [
        "digraph REL {",
        f'graph [rankdir=LR, splines=true, nodesep=0.3, ranksep={1.0 if subset else 1.3}, fontname="{FONT}", pad=0.3, '
        f'labelloc=t, fontsize=26, label="{esc(title)}"];',
        f'node [shape=plain, fontname="{FONT}", fontsize=10];',
        f'edge [fontname="{FONT}", fontsize=9, color="#666666", dir=both, arrowsize=0.8];',
    ]
    for name in TABLES:
        if name not in shown:
            continue
        t = TABLES[name]
        if subset and name not in subset:
            pk = [c for c, _, o in t["cols"] if o.get("pk")]
            lines.append(collapsed(name, t["domain"], port=pk[0], extra=f'<BR/><FONT POINT-SIZE="9">PK {esc(", ".join(pk))}</FONT>'))
            continue
        fill, line = DOMAIN_COLOURS[t["domain"]]
        rows = [f'<TR><TD COLSPAN="3" BGCOLOR="{line}"><FONT COLOR="white"><B>{esc(name)}</B></FONT></TD></TR>']
        for cname, typ, o in t["cols"]:
            keys = []
            if o.get("pk"):
                keys.append("PK")
            if o.get("fk"):
                keys.append("FK")
            if o.get("xref"):
                keys.append("XR")
            if o.get("unique"):
                keys.append("UQ")
            k = ",".join(keys)
            nm = esc(cname)
            if o.get("pk"):
                nm = f"<B><U>{nm}</U></B>"
            ty = esc(typ) + ("" if o.get("null") else " NN")
            if o.get("enc"):
                ty += f' <FONT COLOR="{ENC_COL}"><B>AE-{"Det" if o["enc"] == "DET" else "Rnd"}</B></FONT>'
            rows.append(f'<TR><TD ALIGN="LEFT" PORT="k_{cname}">{('<FONT POINT-SIZE="8">'+k+'</FONT>') if k else ' '}</TD>'
                        f'<TD ALIGN="LEFT">{nm}</TD><TD ALIGN="LEFT" PORT="{cname}"><FONT POINT-SIZE="9">{ty}</FONT></TD></TR>')
        lines.append(f'"{name}" [label=<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="2" '
                     f'BGCOLOR="{fill}" COLOR="{line}">{"".join(rows)}</TABLE>>];')
    for name, t in TABLES.items():
        if subset and name not in subset:
            continue
        for cname, _typ, o in t["cols"]:
            if o.get("fk"):
                tt, tc = o["fk"].split(".")
                tail = "teeodot" if o.get("null") else "teetee"
                lines.append(f'"{tt}":"{tc}":e -> "{name}":"k_{cname}":w [arrowtail={tail}, arrowhead=crowodot];')
    # cross-store reference (UploadId -> MongoDB VaccinationUpload)
    if not subset or "VaccinationRecord" in subset:
      lines.append('"VaccinationUpload (MongoDB)" [shape=box, style="dashed,rounded", color="#C77700", '
                 'fontsize=11, label="MongoDB\\nVaccinationUpload._id"];')
      lines.append('"VaccinationUpload (MongoDB)" -> "VaccinationRecord":"k_UploadId":w '
                 '[style=dashed, color="#C77700", arrowtail=teeodot, arrowhead=crowodot, label="cross-store ref"];')
    legend = legend_rows([
        "<B>Legend</B>",
        "PK primary key   FK foreign key   UQ unique",
        "XR cross-store reference (not enforced by SQL Server)",
        "NN NOT NULL",
        f'<FONT COLOR="{ENC_COL}"><B>AE-Det / AE-Rnd</B></FONT> Always Encrypted',
        "(deterministic / randomised) column",
        "Lines run from the referenced PK (┼) to the FK (○&lt;)",
    ] + (["Dashed grey box = table detailed in another view"] if subset else []))
    lines.append(f'Legend [label=<<TABLE BORDER="1" CELLBORDER="0" CELLPADDING="3" BGCOLOR="white">{legend}</TABLE>>];')
    lines.append("}")
    render("\n".join(lines), fname)


# ---------------------------------------------------------------------------
# Figure 3: document logical model (MongoDB)
# ---------------------------------------------------------------------------
DOC_SHAPES = {
    "VaccinationUpload": [
        ("_id", "ObjectId", "UploadId"),
        ("PRSId", "string", "ref → Person (SQL)"),
        ("UploadedByUserId", "int", "ref → UserAccount (SQL)"),
        ("Format", "string", "FHIR_JSON | FHIR_XML | PDF | IMAGE"),
        ("SourceCountry", "string", "ISO 3166 alpha-2"),
        ("UploadedAt", "date", ""),
        ("ProcessingStatus", "string", "Received | Parsed | NeedsReview | Failed"),
        ("OriginalContent", "object | binData", "FHIR bundle as received, CSFLE-encrypted"),
        ("File", "object", "embedded: GridFsId, FileName, ContentType, SizeBytes, Sha256"),
        ("ExtractedDoses[]", "array<object>", "embedded: VaccineCode, DoseNumber, OccurrenceDateTime, LotNumber, ... VaccinationRecordId"),
        ("DataQualityFlags[]", "array<string>", "e.g. DUPLICATE_DOSE_NUMBER"),
    ],
    "AuditLog": [
        ("_id", "ObjectId", "AuditLogId"),
        ("Timestamp", "date", "time-series timeField"),
        ("Actor", "object", "embedded: UserId, Username, Roles[]"),
        ("Action", "string", "READ | DECRYPT | CREATE | UPDATE | DELETE | LOGIN"),
        ("Target", "object", "embedded: Store, TargetEntity, TargetRecordId, PRSId"),
        ("Outcome", "string", "Allowed | Denied"),
        ("IPAddress", "string", ""),
        ("Details", "object", "free-form, varies by action"),
    ],
    "Notification": [
        ("_id", "ObjectId", "NotificationId"),
        ("PRSId", "string", "ref → Person (SQL)"),
        ("NotificationType", "string", "STOCK_NEARBY | LIMIT_WARNING | VACCINATION_DUE | NEWS"),
        ("Channel[]", "array<string>", "App | SMS | Email"),
        ("CreatedAt / ReadAt", "date", "TTL index on CreatedAt"),
        ("StoreId", "int", "optional ref → Store (SQL)"),
        ("Payload", "object", "varies by type (polymorphic)"),
    ],
    "Announcement": [
        ("_id", "ObjectId", "AnnouncementId"),
        ("Title / Body", "string", ""),
        ("Category", "string", "News | VaccinationSchedule | StockUpdate"),
        ("Regions[]", "array<string>", ""),
        ("PublishedBy", "object", "embedded snapshot: OfficialId, FullName"),
        ("PublishedAt", "date", ""),
        ("Attachments[]", "array<object>", "embedded: GridFsId, ContentType (images, PDFs)"),
    ],
    "GridFS bucket: PRSFiles": [
        ("PRSFiles.files", "collection", "file metadata: _id, length, uploadDate, metadata{PRSId, Purpose}"),
        ("PRSFiles.chunks", "collection", "255 KB binary chunks of PDFs / images"),
    ],
}


def document():
    lines = [
        "digraph DOC {",
        f'graph [rankdir=LR, nodesep=0.5, ranksep=1.0, fontname="{FONT}", pad=0.3, labelloc=t, fontsize=24, '
        'label="Figure 3. PRS document logical model (MongoDB)"];',
        f'node [shape=plain, fontname="{FONT}", fontsize=11];',
        f'edge [fontname="{FONT}", fontsize=10, color="#666666"];',
    ]
    for name, fields in DOC_SHAPES.items():
        dom = COLLECTIONS.get(name, {}).get("domain", "vaccination")
        fill, line = DOMAIN_COLOURS[dom]
        rows = [f'<TR><TD COLSPAN="3" BGCOLOR="{line}"><FONT COLOR="white"><B>{esc(name)}</B></FONT></TD></TR>']
        for f, t, note in fields:
            fn = esc(f)
            if f.endswith("[]") or t.startswith("object"):
                fn = f"<I>{fn}</I>"
            if "CSFLE" in note:
                fn = f'<FONT COLOR="{ENC_COL}"><B>{fn} [E]</B></FONT>'
            rows.append(f'<TR><TD ALIGN="LEFT" PORT="{esc(f.split()[0].rstrip('[]'))}">{fn}</TD><TD ALIGN="LEFT"><FONT POINT-SIZE="9">{esc(t)}</FONT></TD>'
                        f'<TD ALIGN="LEFT">{('<FONT POINT-SIZE="9" COLOR="#444444">'+esc(note)+'</FONT>') if note else ' '}</TD></TR>')
        lines.append(f'"{name}" [label=<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="3" '
                     f'BGCOLOR="{fill}" COLOR="{line}">{"".join(rows)}</TABLE>>];')
    sql = '<TR><TD BGCOLOR="#3B6FD8"><FONT COLOR="white"><B>MS SQL Server (system of record)</B></FONT></TD></TR>'
    for t in ["Person.PRSId", "UserAccount.UserId", "Store.StoreId", "GovernmentOfficial.OfficialId",
              "VaccinationRecord.VaccinationRecordId / UploadId"]:
        sql += f'<TR><TD ALIGN="LEFT" PORT="{t.split(".")[0]}">{esc(t)}</TD></TR>'
    lines.append(f'SQL [label=<<TABLE BORDER="1" CELLBORDER="0" CELLPADDING="3" BGCOLOR="#F5F5F5" COLOR="#3B6FD8">{sql}</TABLE>>];')
    E = 'style=dashed, color="#3B6FD8", fontcolor="#3B6FD8"'
    lines += [
        f'SQL:Person -> VaccinationUpload:PRSId [{E}, label="PRSId"];',
        f'SQL:UserAccount -> VaccinationUpload:UploadedByUserId [{E}, label="UserId"];',
        f'SQL:VaccinationRecord -> VaccinationUpload:_id [{E}, dir=both, label="UploadId ↔ _id"];',
        f'SQL:UserAccount -> AuditLog:Actor [{E}, label="UserId"];',
        f'SQL:Person -> Notification:PRSId [{E}, label="PRSId"];',
        f'SQL:Store -> Notification:StoreId [{E}, label="StoreId"];',
        f'SQL:GovernmentOfficial -> Announcement:PublishedBy [{E}, label="OfficialId"];',
        '"VaccinationUpload":File:e -> "GridFS bucket: PRSFiles":"PRSFiles.files" [label="File.GridFsId", color="#C77700"];',
        '"Announcement":Attachments:e -> "GridFS bucket: PRSFiles":"PRSFiles.files" [label="GridFsId", color="#1F8A99"];',
    ]
    legend = legend_rows([
        "<B>Legend</B>",
        "<I>italic</I> = embedded sub-document / array",
        f'<FONT COLOR="{ENC_COL}"><B>[E]</B></FONT> = client-side field-level encryption',
        '<FONT COLOR="#3B6FD8">dashed</FONT> = reference by shared key to SQL Server',
        "solid = reference to GridFS file",
    ])
    lines.append(f'Legend [label=<<TABLE BORDER="1" CELLBORDER="0" CELLPADDING="3" BGCOLOR="white">{legend}</TABLE>>];')
    lines.append("}")
    render("\n".join(lines), "fig3_document_model")


VIEWS = [
    ("a", "people, identity, access and public information",
     ["Person", "NationalIdentifier", "IdentifierType", "FamilyLink", "UserAccount", "Role", "Permission",
      "UserRole", "RolePermission", "AuditLog", "GovernmentOfficial", "Notification", "Announcement"]),
    ("b", "merchants and supply chain",
     ["Merchant", "Store", "CriticalItem", "StockLevel", "PurchaseLimit", "PurchaseSchedule",
      "Purchase", "PurchaseLine", "Alert"]),
    ("c", "vaccination and border control",
     ["Vaccine", "VaccinationPolicy", "VaccinationRecord", "Verification", "VaccinationUpload", "BorderCheck"]),
]

if __name__ == "__main__":
    conceptual()
    relational()
    document()
    for k, label, members in VIEWS:
        conceptual([m for m in members if m not in ("UserRole", "RolePermission")], f"fig1{k}_conceptual_view",
                   f"Figure 1{k}. Conceptual ER model, detail view: {label}")
        rel = [m for m in members if m in TABLES]
        relational(rel, f"fig2{k}_relational_view", f"Figure 2{k}. Relational model, detail view: {label}")
    print("diagrams written to", OUT)
