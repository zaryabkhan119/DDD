"""Store an unstructured vaccination certificate (PDF or image) in GridFS and
register it as a VaccinationUpload awaiting manual review by an official.

Usage: python3 pdf_upload.py <file.pdf> <PRSId> <uploaded_by_user_id> <country>
"""
import hashlib
import mimetypes
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import gridfs
from pymongo import MongoClient


def upload(path, prs_id, user_id, country, mdb):
    data = Path(path).read_bytes()
    ctype = mimetypes.guess_type(path)[0] or "application/pdf"
    sha = hashlib.sha256(data).hexdigest()
    bucket = gridfs.GridFSBucket(mdb, bucket_name="PRSFiles")
    gid = bucket.upload_from_stream(Path(path).name, data,
                                    metadata={"PRSId": prs_id, "Purpose": "VaccinationEvidence", "ContentType": ctype})
    doc = {
        "PRSId": prs_id,
        "UploadedByUserId": user_id,
        "Format": "PDF" if ctype == "application/pdf" else "IMAGE",
        "SourceCountry": country,
        "UploadedAt": datetime.now(timezone.utc),
        "ProcessingStatus": "NeedsReview",       # nothing machine-readable: an official keys in the doses
        "File": {"GridFsId": gid, "FileName": Path(path).name, "ContentType": ctype,
                 "SizeBytes": len(data), "Sha256": sha},
        "ExtractedDoses": [],
        "DataQualityFlags": ["UNSTRUCTURED_SOURCE"],
    }
    return mdb.VaccinationUpload.insert_one(doc).inserted_id


if __name__ == "__main__":
    mdb = MongoClient(os.getenv("PRS_MONGO_URI", "mongodb://localhost:27017")).PRS
    print("UploadId =", upload(sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4], mdb))
