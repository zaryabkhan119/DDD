"""Single source of truth for the PRS data model.

Every diagram, the SQL Server DDL and the report tables are generated from
these definitions, so entity / table / collection names stay identical
across the conceptual, relational and document models.
"""

# ---------------------------------------------------------------------------
# Relational tables (MS SQL Server)
# Column = (name, sql_type, options)
#   pk, fk="Table.Column", null, unique, identity, default, check,
#   enc="DET"|"RND" (Always Encrypted deterministic / randomised),
#   sens=True (sensitive personal data, protected by TDE + RBAC)
# ---------------------------------------------------------------------------

def C(name, typ, **kw):
    return (name, typ, kw)


TABLES = {
    # ---------------- Identity & privacy ----------------
    "IdentifierType": dict(
        domain="identity",
        desc="Lookup of accepted national identifier types (Passport, Driving Licence, BRP, NHS Number).",
        cols=[
            C("IdentifierTypeCode", "VARCHAR(20)", pk=True),
            C("TypeName", "NVARCHAR(60)", unique=True),
            C("IssuingAuthority", "NVARCHAR(120)", null=True),
        ]),
    "Person": dict(
        domain="identity",
        desc="Every enrolled individual (resident, visitor or child). PRSId is the system-wide identifier.",
        cols=[
            C("PRSId", "CHAR(12)", pk=True, default="generated from SEQUENCE"),
            C("FirstName", "NVARCHAR(100)", sens=True),
            C("LastName", "NVARCHAR(100)", sens=True),
            C("DateOfBirth", "DATE", enc="RND", sens=True),
            C("BirthYearDigit", "TINYINT", check="BirthYearDigit BETWEEN 0 AND 9"),
            C("Email", "NVARCHAR(255)", null=True, sens=True),
            C("Phone", "VARCHAR(20)", null=True, sens=True),
            C("HomePostcode", "VARCHAR(10)", null=True, sens=True),
            C("ResidencyStatus", "VARCHAR(10)", check="ResidencyStatus IN ('Resident','Visitor')"),
            C("NationalityCode", "CHAR(2)", null=True),
            C("EnrolledAt", "DATETIME2", default="SYSUTCDATETIME()"),
            C("IsActive", "BIT", default="1"),
        ]),
    "NationalIdentifier": dict(
        domain="identity",
        desc="Mapping repository: one or more national identifiers per person, value encrypted.",
        cols=[
            C("NationalIdentifierId", "INT", pk=True, identity=True),
            C("PRSId", "CHAR(12)", fk="Person.PRSId"),
            C("IdentifierTypeCode", "VARCHAR(20)", fk="IdentifierType.IdentifierTypeCode"),
            C("IdentifierValue", "NVARCHAR(50)", enc="DET", sens=True),
            C("IssuingCountryCode", "CHAR(2)"),
            C("ExpiryDate", "DATE", null=True),
            C("IsPrimary", "BIT", default="0"),
        ],
        uniques=[("IdentifierTypeCode", "IssuingCountryCode", "IdentifierValue")]),
    "FamilyLink": dict(
        domain="identity",
        desc="Associative entity: a guardian enrols dependants (children under 18). Two FKs to Person.",
        cols=[
            C("GuardianPRSId", "CHAR(12)", pk=True, fk="Person.PRSId"),
            C("DependentPRSId", "CHAR(12)", pk=True, fk="Person.PRSId"),
            C("Relationship", "VARCHAR(15)", check="Relationship IN ('Parent','LegalGuardian')"),
            C("LinkedAt", "DATETIME2", default="SYSUTCDATETIME()"),
        ],
        checks=["GuardianPRSId <> DependentPRSId"]),
    # ---------------- Government ----------------
    "GovernmentOfficial": dict(
        domain="government",
        desc="Government staff who set rules, verify merchants/vaccinations and run border checks.",
        cols=[
            C("OfficialId", "INT", pk=True, identity=True),
            C("StaffNumber", "VARCHAR(20)", unique=True),
            C("FullName", "NVARCHAR(150)"),
            C("Department", "NVARCHAR(100)"),
            C("JobTitle", "NVARCHAR(100)"),
            C("WorkEmail", "NVARCHAR(255)", unique=True),
        ]),
    # ---------------- Security / RBAC ----------------
    "UserAccount": dict(
        domain="security",
        desc="Login for a member of the public, a store (one per location) or an official.",
        cols=[
            C("UserId", "INT", pk=True, identity=True),
            C("Username", "NVARCHAR(100)", unique=True),
            C("PasswordHash", "VARBINARY(64)"),
            C("AccountType", "VARCHAR(10)", check="AccountType IN ('Public','Merchant','Official')"),
            C("PRSId", "CHAR(12)", null=True, fk="Person.PRSId"),
            C("StoreId", "INT", null=True, fk="Store.StoreId"),
            C("OfficialId", "INT", null=True, fk="GovernmentOfficial.OfficialId"),
            C("MfaEnabled", "BIT", default="0"),
            C("Status", "VARCHAR(10)", default="'Active'", check="Status IN ('Active','Locked','Disabled')"),
            C("CreatedAt", "DATETIME2", default="SYSUTCDATETIME()"),
            C("LastLoginAt", "DATETIME2", null=True),
        ],
        checks=["(AccountType = 'Public' AND PRSId IS NOT NULL AND StoreId IS NULL AND OfficialId IS NULL) OR "
                "(AccountType = 'Merchant' AND StoreId IS NOT NULL AND PRSId IS NULL AND OfficialId IS NULL) OR "
                "(AccountType = 'Official' AND OfficialId IS NOT NULL AND PRSId IS NULL AND StoreId IS NULL)"],
        filtered_uniques=["PRSId", "OfficialId"]),
    "Role": dict(
        domain="security",
        desc="RBAC role, e.g. Citizen, StoreOperator, VaccinationVerifier, IdentityOfficer, Auditor.",
        cols=[
            C("RoleId", "INT", pk=True, identity=True),
            C("RoleName", "VARCHAR(50)", unique=True),
            C("Description", "NVARCHAR(255)", null=True),
        ]),
    "Permission": dict(
        domain="security",
        desc="Fine-grained permission, e.g. DECRYPT_NATIONAL_ID, VERIFY_VACCINATION, SET_PURCHASE_LIMIT.",
        cols=[
            C("PermissionId", "INT", pk=True, identity=True),
            C("PermissionCode", "VARCHAR(50)", unique=True),
            C("Description", "NVARCHAR(255)", null=True),
        ]),
    "UserRole": dict(
        domain="security", junction=True,
        desc="Junction table resolving UserAccount M:N Role.",
        cols=[
            C("UserId", "INT", pk=True, fk="UserAccount.UserId"),
            C("RoleId", "INT", pk=True, fk="Role.RoleId"),
            C("AssignedAt", "DATETIME2", default="SYSUTCDATETIME()"),
        ]),
    "RolePermission": dict(
        domain="security", junction=True,
        desc="Junction table resolving Role M:N Permission.",
        cols=[
            C("RoleId", "INT", pk=True, fk="Role.RoleId"),
            C("PermissionId", "INT", pk=True, fk="Permission.PermissionId"),
        ]),
    # ---------------- Merchants & supply ----------------
    "Merchant": dict(
        domain="supply",
        desc="Enrolled business (pharmacy, grocery) identified by its business licence number.",
        cols=[
            C("MerchantId", "INT", pk=True, identity=True),
            C("BusinessLicenceNumber", "VARCHAR(30)", unique=True),
            C("BusinessName", "NVARCHAR(150)"),
            C("BusinessType", "VARCHAR(15)", check="BusinessType IN ('Pharmacy','Grocery','Supermarket','Other')"),
            C("RegisteredAddress", "NVARCHAR(255)"),
            C("ContactEmail", "NVARCHAR(255)"),
            C("EnrolmentStatus", "VARCHAR(10)", default="'Pending'", check="EnrolmentStatus IN ('Pending','Verified','Suspended')"),
            C("EnrolledAt", "DATETIME2", default="SYSUTCDATETIME()"),
            C("VerifiedByOfficialId", "INT", null=True, fk="GovernmentOfficial.OfficialId"),
        ]),
    "Store": dict(
        domain="supply",
        desc="One operational location of a merchant; each store has its own account(s).",
        cols=[
            C("StoreId", "INT", pk=True, identity=True),
            C("MerchantId", "INT", fk="Merchant.MerchantId"),
            C("StoreName", "NVARCHAR(150)"),
            C("AddressLine", "NVARCHAR(255)"),
            C("City", "NVARCHAR(100)"),
            C("Postcode", "VARCHAR(10)"),
            C("GeoLocation", "GEOGRAPHY"),
            C("Phone", "VARCHAR(20)", null=True),
            C("IsOpen", "BIT", default="1"),
        ]),
    "CriticalItem": dict(
        domain="supply",
        desc="Restricted grocery or medical item (face mask, 4-litre milk, testing kit).",
        cols=[
            C("ItemId", "INT", pk=True, identity=True),
            C("ItemName", "NVARCHAR(100)", unique=True),
            C("Category", "VARCHAR(10)", check="Category IN ('Grocery','Medical')"),
            C("UnitOfMeasure", "NVARCHAR(40)"),
        ]),
    "StockLevel": dict(
        domain="supply",
        desc="Associative entity Store x CriticalItem holding the current quantity on hand.",
        cols=[
            C("StoreId", "INT", pk=True, fk="Store.StoreId"),
            C("ItemId", "INT", pk=True, fk="CriticalItem.ItemId"),
            C("QuantityAvailable", "INT", check="QuantityAvailable >= 0"),
            C("LastUpdatedAt", "DATETIME2", default="SYSUTCDATETIME()"),
        ]),
    "PurchaseLimit": dict(
        domain="supply",
        desc="Government rule: max quantity of an item per person per day or week.",
        cols=[
            C("LimitId", "INT", pk=True, identity=True),
            C("ItemId", "INT", fk="CriticalItem.ItemId"),
            C("MaxQuantity", "INT", check="MaxQuantity > 0"),
            C("PeriodType", "VARCHAR(5)", check="PeriodType IN ('Day','Week')"),
            C("EffectiveFrom", "DATE"),
            C("EffectiveTo", "DATE", null=True),
            C("SetByOfficialId", "INT", fk="GovernmentOfficial.OfficialId"),
        ],
        checks=["EffectiveTo IS NULL OR EffectiveTo >= EffectiveFrom"]),
    "PurchaseSchedule": dict(
        domain="supply",
        desc="Government rule: people whose birth year ends in BirthYearDigit may buy the item on AllowedDayOfWeek.",
        cols=[
            C("ScheduleId", "INT", pk=True, identity=True),
            C("ItemId", "INT", fk="CriticalItem.ItemId"),
            C("BirthYearDigit", "TINYINT", check="BirthYearDigit BETWEEN 0 AND 9"),
            C("AllowedDayOfWeek", "TINYINT", check="AllowedDayOfWeek BETWEEN 1 AND 7"),
            C("EffectiveFrom", "DATE"),
            C("EffectiveTo", "DATE", null=True),
            C("SetByOfficialId", "INT", fk="GovernmentOfficial.OfficialId"),
        ],
        uniques=[("ItemId", "BirthYearDigit", "AllowedDayOfWeek", "EffectiveFrom")],
        checks=["EffectiveTo IS NULL OR EffectiveTo >= EffectiveFrom"]),
    "Purchase": dict(
        domain="supply",
        desc="A sale of restricted items to one person at one store.",
        cols=[
            C("PurchaseId", "BIGINT", pk=True, identity=True),
            C("PRSId", "CHAR(12)", fk="Person.PRSId"),
            C("StoreId", "INT", fk="Store.StoreId"),
            C("PurchasedAt", "DATETIME2", default="SYSUTCDATETIME()"),
        ]),
    "PurchaseLine": dict(
        domain="supply",
        desc="Associative entity Purchase x CriticalItem with the quantity bought.",
        cols=[
            C("PurchaseId", "BIGINT", pk=True, fk="Purchase.PurchaseId"),
            C("ItemId", "INT", pk=True, fk="CriticalItem.ItemId"),
            C("Quantity", "INT", check="Quantity > 0"),
        ]),
    "Alert": dict(
        domain="supply",
        desc="Raised when an individual or business breaks a purchase limit or schedule.",
        cols=[
            C("AlertId", "BIGINT", pk=True, identity=True),
            C("AlertType", "VARCHAR(25)", check="AlertType IN ('LimitBreach','ScheduleBreach','MerchantNonCompliance')"),
            C("PRSId", "CHAR(12)", null=True, fk="Person.PRSId"),
            C("StoreId", "INT", null=True, fk="Store.StoreId"),
            C("PurchaseId", "BIGINT", null=True, fk="Purchase.PurchaseId"),
            C("LimitId", "INT", null=True, fk="PurchaseLimit.LimitId"),
            C("ScheduleId", "INT", null=True, fk="PurchaseSchedule.ScheduleId"),
            C("RaisedAt", "DATETIME2", default="SYSUTCDATETIME()"),
            C("Status", "VARCHAR(12)", default="'Open'", check="Status IN ('Open','UnderReview','Closed')"),
            C("ReviewedByOfficialId", "INT", null=True, fk="GovernmentOfficial.OfficialId"),
        ],
        checks=["PRSId IS NOT NULL OR StoreId IS NOT NULL"]),
    # ---------------- Vaccination ----------------
    "Vaccine": dict(
        domain="vaccination",
        desc="Vaccine product, keyed by its SNOMED CT product code (as used in FHIR vaccineCode).",
        cols=[
            C("VaccineCode", "VARCHAR(20)", pk=True),
            C("VaccineName", "NVARCHAR(300)"),
            C("Manufacturer", "NVARCHAR(100)"),
            C("TargetDisease", "NVARCHAR(100)"),
        ]),
    "VaccinationPolicy": dict(
        domain="vaccination",
        desc="Official policy per vaccine and dose: minimum interval and validity period.",
        cols=[
            C("PolicyId", "INT", pk=True, identity=True),
            C("VaccineCode", "VARCHAR(20)", fk="Vaccine.VaccineCode"),
            C("DoseNumber", "TINYINT", check="DoseNumber >= 1"),
            C("MinDaysAfterPreviousDose", "SMALLINT", null=True),
            C("ValidForDays", "SMALLINT", null=True),
            C("EffectiveFrom", "DATE"),
            C("EffectiveTo", "DATE", null=True),
            C("SetByOfficialId", "INT", fk="GovernmentOfficial.OfficialId"),
        ],
        uniques=[("VaccineCode", "DoseNumber", "EffectiveFrom")]),
    "VaccinationRecord": dict(
        domain="vaccination",
        desc="One administered dose for one person, extracted from a FHIR upload or keyed in from a PDF.",
        cols=[
            C("VaccinationRecordId", "BIGINT", pk=True, identity=True),
            C("PRSId", "CHAR(12)", fk="Person.PRSId"),
            C("VaccineCode", "VARCHAR(20)", fk="Vaccine.VaccineCode"),
            C("DoseNumber", "TINYINT", check="DoseNumber >= 1"),
            C("OccurrenceDateTime", "DATETIME2"),
            C("LotNumber", "VARCHAR(30)", null=True),
            C("AdministeredBy", "NVARCHAR(150)", null=True),
            C("CountryCode", "CHAR(2)"),
            C("SourceType", "VARCHAR(10)", check="SourceType IN ('FHIR','PDF','Manual')"),
            C("SourceResourceId", "VARCHAR(64)", null=True),
            C("UploadId", "CHAR(24)", null=True, xref="VaccinationUpload._id"),
            C("PolicyId", "INT", null=True, fk="VaccinationPolicy.PolicyId"),
            C("VerificationStatus", "VARCHAR(10)", default="'Pending'", check="VerificationStatus IN ('Pending','Verified','Rejected')"),
        ],
        filtered_uniques=[("PRSId", "SourceResourceId")]),
    "Verification": dict(
        domain="vaccination",
        desc="History of official checks on a vaccination record (who, how, outcome).",
        cols=[
            C("VerificationId", "BIGINT", pk=True, identity=True),
            C("VaccinationRecordId", "BIGINT", fk="VaccinationRecord.VaccinationRecordId"),
            C("OfficialId", "INT", fk="GovernmentOfficial.OfficialId"),
            C("Method", "VARCHAR(20)", check="Method IN ('IssuerLookup','DocumentReview','FHIRSourceMatch')"),
            C("Outcome", "VARCHAR(10)", check="Outcome IN ('Verified','Rejected','NeedsInfo')"),
            C("Notes", "NVARCHAR(500)", null=True),
            C("VerifiedAt", "DATETIME2", default="SYSUTCDATETIME()"),
        ]),
    "BorderCheck": dict(
        domain="vaccination",
        desc="A traveller's check at a port of entry using their identifier and vaccination status.",
        cols=[
            C("BorderCheckId", "BIGINT", pk=True, identity=True),
            C("PRSId", "CHAR(12)", fk="Person.PRSId"),
            C("NationalIdentifierId", "INT", fk="NationalIdentifier.NationalIdentifierId"),
            C("OfficialId", "INT", fk="GovernmentOfficial.OfficialId"),
            C("PortOfEntry", "NVARCHAR(100)"),
            C("CheckedAt", "DATETIME2", default="SYSUTCDATETIME()"),
            C("Outcome", "VARCHAR(12)", check="Outcome IN ('Cleared','Quarantine','Refused')"),
        ]),
}

# Order tables so that FK targets are created first.
TABLE_ORDER = [
    "IdentifierType", "Person", "NationalIdentifier", "FamilyLink",
    "GovernmentOfficial", "Merchant", "Store",
    "UserAccount", "Role", "Permission", "UserRole", "RolePermission",
    "CriticalItem", "StockLevel", "PurchaseLimit", "PurchaseSchedule",
    "Purchase", "PurchaseLine", "Alert",
    "Vaccine", "VaccinationPolicy", "VaccinationRecord", "Verification", "BorderCheck",
]
assert sorted(TABLE_ORDER) == sorted(TABLES)

# ---------------------------------------------------------------------------
# Document collections (MongoDB) - conceptual attributes
# ---------------------------------------------------------------------------
COLLECTIONS = {
    "VaccinationUpload": dict(
        domain="vaccination",
        desc="Original vaccination evidence: a FHIR bundle (semi-structured) or a PDF/image (unstructured, in GridFS).",
        attrs=["UploadId", "Format", "SourceCountry", "UploadedAt", "ProcessingStatus",
               "OriginalContent (FHIR bundle) \U0001F512", "File (PDF / image)", "ExtractedDoses", "DataQualityFlags"]),
    "AuditLog": dict(
        domain="security",
        desc="Append-only record of every access to sensitive data and every privileged action.",
        attrs=["AuditLogId", "Timestamp", "Action", "TargetEntity", "TargetRecordId", "Outcome", "IPAddress", "Details"]),
    "Notification": dict(
        domain="public",
        desc="Message to an individual: nearby stock, limit warning, vaccination reminder, news.",
        attrs=["NotificationId", "NotificationType", "Channel", "CreatedAt", "ReadAt", "Payload"]),
    "Announcement": dict(
        domain="public",
        desc="Real-time pandemic news and vaccination schedules on the public dashboard.",
        attrs=["AnnouncementId", "Title", "Body", "Category", "Regions", "PublishedAt", "Attachments"]),
}

# ---------------------------------------------------------------------------
# Conceptual relationships
# (A, B, card_at_A, card_at_B, label)
# card codes: "1" exactly one, "01" zero or one, "1N" one or many, "0N" zero or many
# Read as: each B relates to card_at_A of A; each A relates to card_at_B of B.
# ---------------------------------------------------------------------------
RELATIONSHIPS = [
    ("Person", "NationalIdentifier", "1", "1N", "identified by"),
    ("IdentifierType", "NationalIdentifier", "1", "0N", "classifies"),
    ("Person", "FamilyLink", "1", "0N", "is guardian in"),
    ("Person", "FamilyLink", "1", "0N", "is dependant in"),
    ("Person", "UserAccount", "01", "01", "logs in as"),
    ("Store", "UserAccount", "01", "1N", "has accounts"),
    ("GovernmentOfficial", "UserAccount", "01", "1", "logs in as"),
    ("UserAccount", "Role", "0N", "1N", "assigned (M:N)"),
    ("Role", "Permission", "0N", "0N", "grants (M:N)"),
    ("Merchant", "Store", "1", "1N", "operates"),
    ("GovernmentOfficial", "Merchant", "01", "0N", "verifies"),
    ("Store", "StockLevel", "1", "0N", "reports"),
    ("CriticalItem", "StockLevel", "1", "0N", "stocked as"),
    ("CriticalItem", "PurchaseLimit", "1", "0N", "limited by"),
    ("CriticalItem", "PurchaseSchedule", "1", "0N", "scheduled by"),
    ("GovernmentOfficial", "PurchaseLimit", "1", "0N", "sets"),
    ("GovernmentOfficial", "PurchaseSchedule", "1", "0N", "sets"),
    ("Person", "Purchase", "1", "0N", "makes"),
    ("Store", "Purchase", "1", "0N", "records"),
    ("Purchase", "PurchaseLine", "1", "1N", "contains"),
    ("CriticalItem", "PurchaseLine", "1", "0N", "sold in"),
    ("Person", "Alert", "01", "0N", "flagged in"),
    ("Store", "Alert", "01", "0N", "flagged in"),
    ("Purchase", "Alert", "01", "0N", "triggers"),
    ("PurchaseLimit", "Alert", "01", "0N", "breached in"),
    ("PurchaseSchedule", "Alert", "01", "0N", "breached in"),
    ("GovernmentOfficial", "Alert", "01", "0N", "reviews"),
    ("Vaccine", "VaccinationPolicy", "1", "0N", "governed by"),
    ("GovernmentOfficial", "VaccinationPolicy", "1", "0N", "sets"),
    ("Person", "VaccinationRecord", "1", "0N", "receives"),
    ("Vaccine", "VaccinationRecord", "1", "0N", "administered as"),
    ("VaccinationPolicy", "VaccinationRecord", "01", "0N", "assessed against"),
    ("VaccinationUpload", "VaccinationRecord", "01", "0N", "evidences"),
    ("VaccinationRecord", "Verification", "1", "0N", "checked by"),
    ("GovernmentOfficial", "Verification", "1", "0N", "performs"),
    ("Person", "BorderCheck", "1", "0N", "undergoes"),
    ("NationalIdentifier", "BorderCheck", "1", "0N", "presented at"),
    ("GovernmentOfficial", "BorderCheck", "1", "0N", "conducts"),
    ("Person", "VaccinationUpload", "1", "0N", "is subject of"),
    ("UserAccount", "VaccinationUpload", "1", "0N", "submits"),
    ("UserAccount", "AuditLog", "1", "0N", "generates"),
    ("Person", "AuditLog", "01", "0N", "data accessed in"),
    ("Person", "Notification", "1", "0N", "receives"),
    ("Store", "Notification", "01", "0N", "advertised in"),
    ("GovernmentOfficial", "Announcement", "1", "0N", "publishes"),
]

DOMAIN_COLOURS = {
    "identity":    ("#E8F0FE", "#3B6FD8"),
    "government":  ("#F3E8FD", "#8A4FD0"),
    "security":    ("#FDECEA", "#C2412D"),
    "supply":      ("#E7F6EC", "#2E8B57"),
    "vaccination": ("#FFF4E0", "#C77700"),
    "public":      ("#E6F7F8", "#1F8A99"),
}
DOMAIN_LABELS = {
    "identity": "Identity & privacy",
    "government": "Government",
    "security": "Security, RBAC & audit",
    "supply": "Merchants & supply chain",
    "vaccination": "Vaccination & border",
    "public": "Public information",
}


def conceptual_entities():
    """Entities for the conceptual ERD: relational tables (minus pure junction
    tables, which are drawn as M:N relationships) plus document collections."""
    ents = {}
    for name, t in TABLES.items():
        if t.get("junction"):
            continue
        attrs = []
        for cname, _typ, o in t["cols"]:
            if o.get("fk") or o.get("xref"):
                continue  # FKs are a logical-level concern
            attrs.append((cname, o.get("pk", False), o.get("enc"), o.get("sens", False)))
        ents[name] = dict(domain=t["domain"], attrs=attrs, store="SQL")
    for name, c in COLLECTIONS.items():
        attrs = []
        for i, a in enumerate(c["attrs"]):
            enc = "RND" if "\U0001F512" in a else None
            attrs.append((a.replace(" \U0001F512", ""), i == 0, enc, enc is not None))
        ents[name] = dict(domain=c["domain"], attrs=attrs, store="Mongo")
    return ents
