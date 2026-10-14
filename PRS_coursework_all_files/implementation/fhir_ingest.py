"""Automatic ingestion of a machine-readable (FHIR JSON) vaccination report.

Demonstrates the hybrid design end to end:
  1. the original Bundle is stored unchanged in MongoDB (VaccinationUpload),
  2. the patient is matched to a PRS-Id through NationalIdentifier (SQL Server),
  3. each Immunization becomes a VaccinationRecord row (SQL Server) linked back
     to the upload by UploadId, with data-quality problems flagged rather than
     silently "fixed",
  4. the action is written to AuditLog (MongoDB).

Usage: python3 fhir_ingest.py <bundle.json> [uploaded_by_user_id]
"""
import json
import os
import sys
from datetime import datetime, timezone

import pymssql
from pymongo import MongoClient

NHS_NUMBER_SYSTEM = "https://fhir.nhs.uk/Id/nhs-number"
SYSTEM_TO_TYPE = {NHS_NUMBER_SYSTEM: ("NHS_NUMBER", "GB")}

SQL = dict(server=os.getenv("PRS_SQL_HOST", "localhost"), user=os.getenv("PRS_SQL_USER", "sa"),
           password=os.getenv("PRS_SQL_PASSWORD", ""), database="PRS")
MONGO_URI = os.getenv("PRS_MONGO_URI", "mongodb://localhost:27017")


def first_coding(cc):
    c = (cc or {}).get("coding", [{}])[0]
    return c.get("code"), c.get("display")


def fhir_dt(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def ingest(bundle, uploaded_by_user_id, sql, mdb):
    now = datetime.now(timezone.utc)
    flags = []
    resources = [e["resource"] for e in bundle.get("entry", [])]
    patient = next((r for r in resources if r["resourceType"] == "Patient"), None)
    immunizations = [r for r in resources if r["resourceType"] == "Immunization"]

    # --- 1. identity match through the mapping repository -----------------
    ident = (patient or {}).get("identifier", [{}])[0]
    id_type, id_country = SYSTEM_TO_TYPE.get(ident.get("system"), (None, None))
    cur = sql.cursor(as_dict=True)
    cur.execute("""SELECT p.PRSId, p.DateOfBirth FROM dbo.NationalIdentifier ni
                   JOIN dbo.Person p ON p.PRSId = ni.PRSId
                   WHERE ni.IdentifierTypeCode = %s AND ni.IssuingCountryCode = %s AND ni.IdentifierValue = %s""",
                (id_type, id_country, ident.get("value")))
    person = cur.fetchone()
    if not person:
        raise SystemExit("No PRS-Id is mapped to this identifier: the upload is held for manual review.")
    match = "Matched"
    if patient.get("birthDate") and str(person["DateOfBirth"]) != patient["birthDate"]:
        match = "BirthDateMismatch"
        flags.append("BIRTHDATE_MISMATCH")
    prs_id = person["PRSId"]

    # --- 2. normalise each Immunization, keeping the source values --------
    doses = []
    for imm in sorted(immunizations, key=lambda r: r["occurrenceDateTime"]):
        code, name = first_coding(imm.get("vaccineCode"))
        performer = imm.get("performer", [{}])[0].get("actor", {})
        doses.append({
            "SourceResourceId": imm["id"],
            "VaccineCode": code,
            "VaccineName": name,
            "OriginalDoseNumber": imm.get("protocolApplied", [{}])[0].get("doseNumberPositiveInt"),
            "OccurrenceDateTime": fhir_dt(imm["occurrenceDateTime"]),
            "LotNumber": imm.get("lotNumber"),
            "Manufacturer": imm.get("manufacturer", {}).get("display"),
            "Site": first_coding(imm.get("site"))[1],
            "Route": first_coding(imm.get("route"))[1],
            "AdministeredBy": {"OdsCode": performer.get("identifier", {}).get("value"),
                               "Name": performer.get("display")},
            "CountryCode": imm.get("location", {}).get("identifier", {}).get("value"),
            "Status": imm.get("status"),
        })
        if imm.get("status") != "completed":
            flags.append(f"NOT_COMPLETED:{imm['id']}")

    # Dose numbers: the NHS sample labels both doses "1". Keep the original,
    # assign the chronological sequence, and flag it for the verifying official.
    originals = [d["OriginalDoseNumber"] for d in doses]
    if len(set(originals)) != len(originals):
        flags.append("DUPLICATE_DOSE_NUMBER")
    seq = {}
    for d in doses:
        seq[d["VaccineCode"]] = seq.get(d["VaccineCode"], 0) + 1
        d["DoseNumber"] = seq[d["VaccineCode"]]

    # --- 3. store the original evidence in MongoDB ------------------------
    upload = {
        "PRSId": prs_id,
        "UploadedByUserId": uploaded_by_user_id,
        "Format": "FHIR_JSON",
        "SourceCountry": doses[0]["CountryCode"] if doses else None,
        "UploadedAt": now,
        "ProcessingStatus": "Received",
        "OriginalContent": bundle,          # CSFLE-encrypted field in production
        "IdentityMatch": {"IdentifierTypeCode": id_type, "MatchStatus": match},
        "ExtractedDoses": [{k: v for k, v in d.items() if k != "Status" and v is not None} for d in doses],
        "DataQualityFlags": flags,
    }
    upload_id = mdb.VaccinationUpload.insert_one(upload).inserted_id

    # --- 4. structured rows in SQL Server, idempotent on SourceResourceId ---
    prev_date = None
    for i, d in enumerate(doses):
        cur.execute("SELECT 1 AS x FROM dbo.Vaccine WHERE VaccineCode = %s", (d["VaccineCode"],))
        if not cur.fetchone():
            flags.append(f"UNKNOWN_VACCINE:{d['VaccineCode']}")
            continue
        cur.execute("""SELECT TOP (1) PolicyId, MinDaysAfterPreviousDose FROM dbo.VaccinationPolicy
                       WHERE VaccineCode = %s AND DoseNumber = %s AND EffectiveFrom <= %s
                         AND (EffectiveTo IS NULL OR EffectiveTo >= %s) ORDER BY EffectiveFrom DESC""",
                    (d["VaccineCode"], d["DoseNumber"], d["OccurrenceDateTime"].date(), d["OccurrenceDateTime"].date()))
        pol = cur.fetchone()
        if pol and pol["MinDaysAfterPreviousDose"] and prev_date and \
                (d["OccurrenceDateTime"] - prev_date).days < pol["MinDaysAfterPreviousDose"]:
            flags.append(f"INTERVAL_TOO_SHORT:dose{d['DoseNumber']}")
        prev_date = d["OccurrenceDateTime"]
        cur.execute("""
            MERGE dbo.VaccinationRecord AS t
            USING (SELECT %s AS PRSId, %s AS SourceResourceId) AS s
               ON t.PRSId = s.PRSId AND t.SourceResourceId = s.SourceResourceId
            WHEN NOT MATCHED THEN INSERT (PRSId, VaccineCode, DoseNumber, OccurrenceDateTime, LotNumber,
                 AdministeredBy, CountryCode, SourceType, SourceResourceId, UploadId, PolicyId)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, 'FHIR', %s, %s, %s)
            OUTPUT inserted.VaccinationRecordId;""",
                    (prs_id, d["SourceResourceId"], prs_id, d["VaccineCode"], d["DoseNumber"],
                     d["OccurrenceDateTime"].replace(tzinfo=None), d["LotNumber"], d["AdministeredBy"]["Name"],
                     d["CountryCode"], d["SourceResourceId"], str(upload_id), pol["PolicyId"] if pol else None))
        row = cur.fetchone()
        if row:
            mdb.VaccinationUpload.update_one(
                {"_id": upload_id}, {"$set": {f"ExtractedDoses.{i}.VaccinationRecordId": int(row["VaccinationRecordId"])}})
    sql.commit()

    status = "NeedsReview" if flags else "Parsed"
    mdb.VaccinationUpload.update_one({"_id": upload_id},
                                     {"$set": {"ProcessingStatus": status, "DataQualityFlags": flags}})

    # --- 5. audit ------------------------------------------------------------
    mdb.AuditLog.insert_one({
        "Timestamp": now,
        "Actor": {"UserId": uploaded_by_user_id, "Username": "ingest-service", "Roles": ["Citizen"]},
        "Action": "CREATE",
        "Target": {"Store": "MongoDB+SQL", "TargetEntity": "VaccinationUpload",
                   "TargetRecordId": str(upload_id), "PRSId": prs_id},
        "Outcome": "Allowed",
        "IPAddress": "127.0.0.1",
        "Details": {"Format": "FHIR_JSON", "Doses": len(doses), "Flags": flags},
    })
    return upload_id, status, flags


if __name__ == "__main__":
    bundle = json.load(open(sys.argv[1]))
    user = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    sql = pymssql.connect(**SQL)
    mdb = MongoClient(MONGO_URI).PRS
    uid, status, flags = ingest(bundle, user, sql, mdb)
    print(f"UploadId={uid} ProcessingStatus={status} DataQualityFlags={flags}")
