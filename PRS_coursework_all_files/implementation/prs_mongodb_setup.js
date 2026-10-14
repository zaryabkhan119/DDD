// =====================================================================
// Pandemic Resilience System (PRS) - document logical model (MongoDB 7)
// Run with:  mongosh "mongodb://localhost:27017/PRS" prs_mongodb_setup.js
//
// Field names deliberately match the conceptual model and SQL Server
// schema (PRSId, UserId, StoreId, OfficialId, VaccinationRecordId ...),
// so the two stores join on shared identifiers.
// In production OriginalContent is protected with Client-Side Field Level
// Encryption (randomised), so the server only ever sees binData.
// =====================================================================

const prs = db.getSiblingDB("PRS");
for (const c of ["VaccinationUpload", "AuditLog", "Notification", "Announcement", "PRSFiles.files", "PRSFiles.chunks"]) {
  if (prs.getCollectionNames().includes(c)) prs.getCollection(c).drop();
}

const PRSID = { bsonType: "string", pattern: "^PRS[0-9]{9}$" };

// ---------------------------------------------------------------------
// VaccinationUpload: semi-structured (FHIR) and unstructured (PDF/image)
// ---------------------------------------------------------------------
prs.createCollection("VaccinationUpload", {
  validator: { $jsonSchema: {
    bsonType: "object",
    required: ["PRSId", "UploadedByUserId", "Format", "UploadedAt", "ProcessingStatus"],
    properties: {
      PRSId:            PRSID,
      UploadedByUserId: { bsonType: "int" },
      Format:           { enum: ["FHIR_JSON", "FHIR_XML", "PDF", "IMAGE"] },
      SourceCountry:    { bsonType: "string", pattern: "^[A-Z]{2}$" },
      UploadedAt:       { bsonType: "date" },
      ProcessingStatus: { enum: ["Received", "Parsed", "NeedsReview", "Failed"] },
      OriginalContent:  { bsonType: ["object", "binData"],
                          description: "FHIR Bundle exactly as received (CSFLE-encrypted in production)" },
      File: {
        bsonType: "object",
        required: ["GridFsId", "FileName", "ContentType", "SizeBytes", "Sha256"],
        properties: {
          GridFsId:    { bsonType: "objectId" },
          FileName:    { bsonType: "string" },
          ContentType: { enum: ["application/pdf", "image/jpeg", "image/png"] },
          SizeBytes:   { bsonType: ["int", "long"], maximum: 10485760 },
          Sha256:      { bsonType: "string", pattern: "^[0-9a-f]{64}$" }
        }
      },
      ExtractedDoses: {
        bsonType: "array",
        items: {
          bsonType: "object",
          required: ["VaccineCode", "DoseNumber", "OccurrenceDateTime"],
          properties: {
            SourceResourceId:   { bsonType: "string" },
            VaccineCode:        { bsonType: "string" },
            VaccineName:        { bsonType: "string" },
            DoseNumber:         { bsonType: "int", minimum: 1 },
            OriginalDoseNumber: { bsonType: "int" },
            OccurrenceDateTime: { bsonType: "date" },
            LotNumber:          { bsonType: "string" },
            Manufacturer:       { bsonType: "string" },
            Site:               { bsonType: "string" },
            Route:              { bsonType: "string" },
            AdministeredBy:     { bsonType: "object" },
            CountryCode:        { bsonType: "string" },
            VaccinationRecordId:{ bsonType: ["long", "int"] }
          }
        }
      },
      DataQualityFlags: { bsonType: "array", items: { bsonType: "string" } },
      IdentityMatch: {
        bsonType: "object",
        properties: {
          IdentifierTypeCode: { bsonType: "string" },
          MatchStatus:        { enum: ["Matched", "BirthDateMismatch", "NoMatch"] }
        }
      }
    },
    // a FHIR upload must carry content; a PDF/IMAGE upload must carry a file
    oneOf: [
      { properties: { Format: { enum: ["FHIR_JSON", "FHIR_XML"] } }, required: ["OriginalContent"] },
      { properties: { Format: { enum: ["PDF", "IMAGE"] } },          required: ["File"] }
    ]
  } },
  validationLevel: "strict",
  validationAction: "error"
});
prs.VaccinationUpload.createIndex({ PRSId: 1, UploadedAt: -1 });
prs.VaccinationUpload.createIndex({ ProcessingStatus: 1, UploadedAt: 1 });  // officials' review queue
prs.VaccinationUpload.createIndex({ "File.Sha256": 1 }, { unique: true, partialFilterExpression: { "File.Sha256": { $exists: true } } });

// ---------------------------------------------------------------------
// AuditLog: append-only, high-volume time-series collection
// ---------------------------------------------------------------------
prs.createCollection("AuditLog", {
  timeseries: { timeField: "Timestamp", metaField: "Actor", granularity: "seconds" }
});
prs.AuditLog.createIndex({ "Actor.UserId": 1, Timestamp: -1 });
prs.AuditLog.createIndex({ "Target.PRSId": 1, Timestamp: -1 });
// Applications connect with a role that has only "insert" + "find" on AuditLog,
// so entries cannot be altered or deleted (see report section 4.3).

// ---------------------------------------------------------------------
// Notification: polymorphic payload, expires after 90 days
// ---------------------------------------------------------------------
prs.createCollection("Notification", {
  validator: { $jsonSchema: {
    bsonType: "object",
    required: ["PRSId", "NotificationType", "Channel", "CreatedAt", "Payload"],
    properties: {
      PRSId:            PRSID,
      NotificationType: { enum: ["STOCK_NEARBY", "LIMIT_WARNING", "VACCINATION_DUE", "NEWS"] },
      Channel:          { bsonType: "array", items: { enum: ["App", "SMS", "Email"] }, minItems: 1 },
      CreatedAt:        { bsonType: "date" },
      ReadAt:           { bsonType: ["date", "null"] },
      StoreId:          { bsonType: "int" },
      Payload:          { bsonType: "object" }
    }
  } }
});
prs.Notification.createIndex({ PRSId: 1, CreatedAt: -1 });
prs.Notification.createIndex({ CreatedAt: 1 }, { expireAfterSeconds: 60 * 60 * 24 * 90 });

// ---------------------------------------------------------------------
// Announcement: public news and vaccination schedules
// ---------------------------------------------------------------------
prs.createCollection("Announcement", {
  validator: { $jsonSchema: {
    bsonType: "object",
    required: ["Title", "Body", "Category", "PublishedBy", "PublishedAt"],
    properties: {
      Title:       { bsonType: "string", maxLength: 200 },
      Body:        { bsonType: "string" },
      Category:    { enum: ["News", "VaccinationSchedule", "StockUpdate"] },
      Regions:     { bsonType: "array", items: { bsonType: "string" } },
      PublishedBy: { bsonType: "object", required: ["OfficialId"],
                     properties: { OfficialId: { bsonType: "int" }, FullName: { bsonType: "string" } } },
      PublishedAt: { bsonType: "date" },
      Attachments: { bsonType: "array", items: { bsonType: "object", required: ["GridFsId", "ContentType"] } }
    }
  } }
});
prs.Announcement.createIndex({ Category: 1, PublishedAt: -1 });
prs.Announcement.createIndex({ Title: "text", Body: "text" });

// GridFS bucket "PRSFiles" (PRSFiles.files / PRSFiles.chunks) is created by the
// driver on first upload; index the metadata used to find a person's files.
prs.getCollection("PRSFiles.files").createIndex({ "metadata.PRSId": 1 });

// ---------------------------------------------------------------------
// Sample documents
// ---------------------------------------------------------------------
prs.Announcement.insertOne({
  Title: "Face mask purchase days",
  Body: "Birth years ending 0 or 2 may buy face masks on Monday, 1 or 3 on Tuesday, 4 or 6 on Wednesday, 5 or 7 on Thursday, 8 or 9 on Friday. Limit 7 per week.",
  Category: "News",
  Regions: ["England"],
  PublishedBy: { OfficialId: 1, FullName: "A. Official" },
  PublishedAt: new Date("2026-10-10T09:00:00Z"),
  Attachments: []
});

prs.Notification.insertOne({
  PRSId: "PRS000000001",
  NotificationType: "STOCK_NEARBY",
  Channel: ["App"],
  CreatedAt: new Date(),
  ReadAt: null,
  StoreId: 1,
  Payload: { ItemId: 1, ItemName: "Face mask", QuantityAvailable: 245, DistanceKm: 0.64,
             EligibleToday: false, NextEligibleDay: "Thursday" }
});

print("PRS MongoDB collections:", prs.getCollectionNames().sort().join(", "));
