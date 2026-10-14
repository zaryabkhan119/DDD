#!/bin/bash
# Rebuild both databases from scratch, run all tests and regenerate every output.
set -e
cd "$(dirname "$0")"; B=../build; mkdir -p $B
export PRS_SQL_PASSWORD='Prs!Passw0rd2026'
python3 diagrams.py $B
python3 gen_sql.py $B/prs_sqlserver_schema.sql
cp prs_mongodb_setup.js fhir_ingest.py pdf_upload.py test_scenarios.sql $B/
S="docker exec mssql /opt/mssql-tools18/bin/sqlcmd -C -S localhost -U sa -P $PRS_SQL_PASSWORD -b"
$S -Q "IF DB_ID('PRS') IS NOT NULL BEGIN ALTER DATABASE PRS SET SINGLE_USER WITH ROLLBACK IMMEDIATE; DROP DATABASE PRS; END"
docker cp $B/prs_sqlserver_schema.sql mssql:/tmp/s.sql; $S -I -i /tmp/s.sql > /dev/null
docker cp $B/prs_mongodb_setup.js mongo:/tmp/m.js; docker exec mongo mongosh --quiet mongodb://localhost:27017/PRS /tmp/m.js
docker cp test_scenarios.sql mssql:/tmp/t.sql
$S -d PRS -I -W -i /tmp/t.sql > $B/test_sql_output.txt
{ echo '$ python3 fhir_ingest.py NHS-Immunization-FHIR-JSON.json 1'; python3 fhir_ingest.py ../NHS-Immunization-FHIR-JSON.json 1
  echo '$ python3 fhir_ingest.py NHS-Immunization-FHIR-JSON.json 1   # same file again'; python3 fhir_ingest.py ../NHS-Immunization-FHIR-JSON.json 1
  echo '$ SELECT ... FROM VaccinationRecord'
  $S -d PRS -W -Q "SET NOCOUNT ON; SELECT VaccinationRecordId, PRSId, DoseNumber, CAST(OccurrenceDateTime AS DATE) AS OccurrenceDate, SourceResourceId, UploadId, PolicyId, VerificationStatus FROM VaccinationRecord"
} > $B/test_ingest_output.txt
python3 pdf_upload.py $B/sample_certificate.pdf PRS000000001 1 FR > /dev/null
python3 - <<'PY'
from pymongo import MongoClient
from bson import json_util
db = MongoClient().PRS
ex = {"VaccinationUpload_FHIR": db.VaccinationUpload.find_one({"Format": "FHIR_JSON"}),
      "VaccinationUpload_PDF": db.VaccinationUpload.find_one({"Format": "PDF"}),
      "AuditLog": db.AuditLog.find_one(),
      "Notification": db.Notification.find_one(),
      "Announcement": db.Announcement.find_one()}
open("../build/example_documents.json", "w").write(json_util.dumps(ex, indent=2, json_options=json_util.RELAXED_JSON_OPTIONS))
PY
python3 build_report.py $B
cd $B && timeout 300 soffice --headless --convert-to pdf STUDENTID_DDD.docx > /dev/null 2>&1 && echo "PDF built"
