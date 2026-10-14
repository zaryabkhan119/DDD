"""Generate the SQL Server DDL (prs_sqlserver_schema.sql) from model.TABLES."""
import sys
from pathlib import Path

from model import TABLES, TABLE_ORDER

out = Path(sys.argv[1] if len(sys.argv) > 1 else "prs_sqlserver_schema.sql")

L = []
w = L.append
w("""/* =====================================================================
   Pandemic Resilience System (PRS) - relational logical model
   Target: Microsoft SQL Server 2019+ (Azure SQL compatible)
   Generated from the same model definition as Figures 1 and 2.

   Encryption: columns marked "-- AE:" are protected with Always Encrypted.
   Column encryption keys are created per environment by the SSMS
   Always Encrypted wizard (or PowerShell), so the ENCRYPTED WITH clause is
   shown as a comment and the script runs as-is on a dev instance.
   The whole database is additionally protected at rest with TDE.
   ===================================================================== */

IF DB_ID('PRS') IS NULL CREATE DATABASE PRS;
GO
USE PRS;
GO
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

CREATE SEQUENCE dbo.PRSIdSeq AS INT START WITH 1 INCREMENT BY 1;
GO
""")

for name in TABLE_ORDER:
    t = TABLES[name]
    w(f"-- {t['desc']}")
    w(f"CREATE TABLE dbo.{name} (")
    body = []
    pks = [c for c, _, o in t["cols"] if o.get("pk")]
    for cname, typ, o in t["cols"]:
        s = f"    {cname} {typ}"
        if o.get("enc") == "DET" and "CHAR" in typ:
            s += " COLLATE Latin1_General_BIN2"
        if o.get("identity"):
            s += " IDENTITY(1,1)"
        s += " NULL" if o.get("null") else " NOT NULL"
        d = o.get("default")
        if d == "generated from SEQUENCE":
            s += f" CONSTRAINT DF_{name}_{cname} DEFAULT ('PRS' + RIGHT('000000000' + CAST(NEXT VALUE FOR dbo.PRSIdSeq AS VARCHAR(9)), 9))"
        elif d:
            s += f" CONSTRAINT DF_{name}_{cname} DEFAULT ({d})"
        if o.get("unique"):
            s += f" CONSTRAINT UQ_{name}_{cname} UNIQUE"
        if o.get("check"):
            s += f" CONSTRAINT CK_{name}_{cname} CHECK ({o['check']})"
        if o.get("enc"):
            kind = "DETERMINISTIC" if o["enc"] == "DET" else "RANDOMIZED"
            s += f"\n        -- AE: ENCRYPTED WITH (COLUMN_ENCRYPTION_KEY = CEK_PRS, ENCRYPTION_TYPE = {kind}, ALGORITHM = 'AEAD_AES_256_CBC_HMAC_SHA_256')"
        body.append(s)
    body.append(f"    CONSTRAINT PK_{name} PRIMARY KEY ({', '.join(pks)})")
    for cname, typ, o in t["cols"]:
        if o.get("fk"):
            tt, tc = o["fk"].split(".")
            body.append(f"    CONSTRAINT FK_{name}_{cname} FOREIGN KEY ({cname}) REFERENCES dbo.{tt}({tc})")
    for i, u in enumerate(t.get("uniques", []), 1):
        body.append(f"    CONSTRAINT UQ_{name}_{i} UNIQUE ({', '.join(u)})")
    for i, c in enumerate(t.get("checks", []), 1):
        body.append(f"    CONSTRAINT CK_{name}_{i} CHECK ({c})")
    # put commas before AE comment lines
    joined = []
    for i, b in enumerate(body):
        sep = "," if i < len(body) - 1 else ""
        if "\n        -- AE:" in b:
            head, tail = b.split("\n", 1)
            joined.append(head + sep + "\n" + tail)
        else:
            joined.append(b + sep)
    w("\n".join(joined))
    w(");")
    w("GO\n")

# Indexes on foreign keys + filtered uniques
w("-- Supporting indexes ------------------------------------------------")
for name in TABLE_ORDER:
    t = TABLES[name]
    pks = [c for c, _, o in t["cols"] if o.get("pk")]
    for cname, _typ, o in t["cols"]:
        if o.get("fk") and not (o.get("pk") and pks[0] == cname):
            w(f"CREATE INDEX IX_{name}_{cname} ON dbo.{name}({cname});")
    for fu in t.get("filtered_uniques", []):
        cols = fu if isinstance(fu, tuple) else (fu,)
        nn = cols[-1]
        w(f"CREATE UNIQUE INDEX UX_{name}_{'_'.join(cols)} ON dbo.{name}({', '.join(cols)}) WHERE {nn} IS NOT NULL;")
w("CREATE INDEX IX_Purchase_PRSId_PurchasedAt ON dbo.Purchase(PRSId, PurchasedAt);")
w("CREATE SPATIAL INDEX SX_Store_GeoLocation ON dbo.Store(GeoLocation);")
w("GO\n")

w(Path(__file__).with_name("sql_tail.sql").read_text())
out.write_text("\n".join(L))
print("wrote", out)
