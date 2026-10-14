/* =====================================================================
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

-- Lookup of accepted national identifier types (Passport, Driving Licence, BRP, NHS Number).
CREATE TABLE dbo.IdentifierType (
    IdentifierTypeCode VARCHAR(20) NOT NULL,
    TypeName NVARCHAR(60) NOT NULL CONSTRAINT UQ_IdentifierType_TypeName UNIQUE,
    IssuingAuthority NVARCHAR(120) NULL,
    CONSTRAINT PK_IdentifierType PRIMARY KEY (IdentifierTypeCode)
);
GO

-- Every enrolled individual (resident, visitor or child). PRSId is the system-wide identifier.
CREATE TABLE dbo.Person (
    PRSId CHAR(12) NOT NULL CONSTRAINT DF_Person_PRSId DEFAULT ('PRS' + RIGHT('000000000' + CAST(NEXT VALUE FOR dbo.PRSIdSeq AS VARCHAR(9)), 9)),
    FirstName NVARCHAR(100) NOT NULL,
    LastName NVARCHAR(100) NOT NULL,
    DateOfBirth DATE NOT NULL,
        -- AE: ENCRYPTED WITH (COLUMN_ENCRYPTION_KEY = CEK_PRS, ENCRYPTION_TYPE = RANDOMIZED, ALGORITHM = 'AEAD_AES_256_CBC_HMAC_SHA_256')
    BirthYearDigit TINYINT NOT NULL CONSTRAINT CK_Person_BirthYearDigit CHECK (BirthYearDigit BETWEEN 0 AND 9),
    Email NVARCHAR(255) NULL,
    Phone VARCHAR(20) NULL,
    HomePostcode VARCHAR(10) NULL,
    ResidencyStatus VARCHAR(10) NOT NULL CONSTRAINT CK_Person_ResidencyStatus CHECK (ResidencyStatus IN ('Resident','Visitor')),
    NationalityCode CHAR(2) NULL,
    EnrolledAt DATETIME2 NOT NULL CONSTRAINT DF_Person_EnrolledAt DEFAULT (SYSUTCDATETIME()),
    IsActive BIT NOT NULL CONSTRAINT DF_Person_IsActive DEFAULT (1),
    CONSTRAINT PK_Person PRIMARY KEY (PRSId)
);
GO

-- Mapping repository: one or more national identifiers per person, value encrypted.
CREATE TABLE dbo.NationalIdentifier (
    NationalIdentifierId INT IDENTITY(1,1) NOT NULL,
    PRSId CHAR(12) NOT NULL,
    IdentifierTypeCode VARCHAR(20) NOT NULL,
    IdentifierValue NVARCHAR(50) COLLATE Latin1_General_BIN2 NOT NULL,
        -- AE: ENCRYPTED WITH (COLUMN_ENCRYPTION_KEY = CEK_PRS, ENCRYPTION_TYPE = DETERMINISTIC, ALGORITHM = 'AEAD_AES_256_CBC_HMAC_SHA_256')
    IssuingCountryCode CHAR(2) NOT NULL,
    ExpiryDate DATE NULL,
    IsPrimary BIT NOT NULL CONSTRAINT DF_NationalIdentifier_IsPrimary DEFAULT (0),
    CONSTRAINT PK_NationalIdentifier PRIMARY KEY (NationalIdentifierId),
    CONSTRAINT FK_NationalIdentifier_PRSId FOREIGN KEY (PRSId) REFERENCES dbo.Person(PRSId),
    CONSTRAINT FK_NationalIdentifier_IdentifierTypeCode FOREIGN KEY (IdentifierTypeCode) REFERENCES dbo.IdentifierType(IdentifierTypeCode),
    CONSTRAINT UQ_NationalIdentifier_1 UNIQUE (IdentifierTypeCode, IssuingCountryCode, IdentifierValue)
);
GO

-- Associative entity: a guardian enrols dependants (children under 18). Two FKs to Person.
CREATE TABLE dbo.FamilyLink (
    GuardianPRSId CHAR(12) NOT NULL,
    DependentPRSId CHAR(12) NOT NULL,
    Relationship VARCHAR(15) NOT NULL CONSTRAINT CK_FamilyLink_Relationship CHECK (Relationship IN ('Parent','LegalGuardian')),
    LinkedAt DATETIME2 NOT NULL CONSTRAINT DF_FamilyLink_LinkedAt DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_FamilyLink PRIMARY KEY (GuardianPRSId, DependentPRSId),
    CONSTRAINT FK_FamilyLink_GuardianPRSId FOREIGN KEY (GuardianPRSId) REFERENCES dbo.Person(PRSId),
    CONSTRAINT FK_FamilyLink_DependentPRSId FOREIGN KEY (DependentPRSId) REFERENCES dbo.Person(PRSId),
    CONSTRAINT CK_FamilyLink_1 CHECK (GuardianPRSId <> DependentPRSId)
);
GO

-- Government staff who set rules, verify merchants/vaccinations and run border checks.
CREATE TABLE dbo.GovernmentOfficial (
    OfficialId INT IDENTITY(1,1) NOT NULL,
    StaffNumber VARCHAR(20) NOT NULL CONSTRAINT UQ_GovernmentOfficial_StaffNumber UNIQUE,
    FullName NVARCHAR(150) NOT NULL,
    Department NVARCHAR(100) NOT NULL,
    JobTitle NVARCHAR(100) NOT NULL,
    WorkEmail NVARCHAR(255) NOT NULL CONSTRAINT UQ_GovernmentOfficial_WorkEmail UNIQUE,
    CONSTRAINT PK_GovernmentOfficial PRIMARY KEY (OfficialId)
);
GO

-- Enrolled business (pharmacy, grocery) identified by its business licence number.
CREATE TABLE dbo.Merchant (
    MerchantId INT IDENTITY(1,1) NOT NULL,
    BusinessLicenceNumber VARCHAR(30) NOT NULL CONSTRAINT UQ_Merchant_BusinessLicenceNumber UNIQUE,
    BusinessName NVARCHAR(150) NOT NULL,
    BusinessType VARCHAR(15) NOT NULL CONSTRAINT CK_Merchant_BusinessType CHECK (BusinessType IN ('Pharmacy','Grocery','Supermarket','Other')),
    RegisteredAddress NVARCHAR(255) NOT NULL,
    ContactEmail NVARCHAR(255) NOT NULL,
    EnrolmentStatus VARCHAR(10) NOT NULL CONSTRAINT DF_Merchant_EnrolmentStatus DEFAULT ('Pending') CONSTRAINT CK_Merchant_EnrolmentStatus CHECK (EnrolmentStatus IN ('Pending','Verified','Suspended')),
    EnrolledAt DATETIME2 NOT NULL CONSTRAINT DF_Merchant_EnrolledAt DEFAULT (SYSUTCDATETIME()),
    VerifiedByOfficialId INT NULL,
    CONSTRAINT PK_Merchant PRIMARY KEY (MerchantId),
    CONSTRAINT FK_Merchant_VerifiedByOfficialId FOREIGN KEY (VerifiedByOfficialId) REFERENCES dbo.GovernmentOfficial(OfficialId)
);
GO

-- One operational location of a merchant; each store has its own account(s).
CREATE TABLE dbo.Store (
    StoreId INT IDENTITY(1,1) NOT NULL,
    MerchantId INT NOT NULL,
    StoreName NVARCHAR(150) NOT NULL,
    AddressLine NVARCHAR(255) NOT NULL,
    City NVARCHAR(100) NOT NULL,
    Postcode VARCHAR(10) NOT NULL,
    GeoLocation GEOGRAPHY NOT NULL,
    Phone VARCHAR(20) NULL,
    IsOpen BIT NOT NULL CONSTRAINT DF_Store_IsOpen DEFAULT (1),
    CONSTRAINT PK_Store PRIMARY KEY (StoreId),
    CONSTRAINT FK_Store_MerchantId FOREIGN KEY (MerchantId) REFERENCES dbo.Merchant(MerchantId)
);
GO

-- Login for a member of the public, a store (one per location) or an official.
CREATE TABLE dbo.UserAccount (
    UserId INT IDENTITY(1,1) NOT NULL,
    Username NVARCHAR(100) NOT NULL CONSTRAINT UQ_UserAccount_Username UNIQUE,
    PasswordHash VARBINARY(64) NOT NULL,
    AccountType VARCHAR(10) NOT NULL CONSTRAINT CK_UserAccount_AccountType CHECK (AccountType IN ('Public','Merchant','Official')),
    PRSId CHAR(12) NULL,
    StoreId INT NULL,
    OfficialId INT NULL,
    MfaEnabled BIT NOT NULL CONSTRAINT DF_UserAccount_MfaEnabled DEFAULT (0),
    Status VARCHAR(10) NOT NULL CONSTRAINT DF_UserAccount_Status DEFAULT ('Active') CONSTRAINT CK_UserAccount_Status CHECK (Status IN ('Active','Locked','Disabled')),
    CreatedAt DATETIME2 NOT NULL CONSTRAINT DF_UserAccount_CreatedAt DEFAULT (SYSUTCDATETIME()),
    LastLoginAt DATETIME2 NULL,
    CONSTRAINT PK_UserAccount PRIMARY KEY (UserId),
    CONSTRAINT FK_UserAccount_PRSId FOREIGN KEY (PRSId) REFERENCES dbo.Person(PRSId),
    CONSTRAINT FK_UserAccount_StoreId FOREIGN KEY (StoreId) REFERENCES dbo.Store(StoreId),
    CONSTRAINT FK_UserAccount_OfficialId FOREIGN KEY (OfficialId) REFERENCES dbo.GovernmentOfficial(OfficialId),
    CONSTRAINT CK_UserAccount_1 CHECK ((AccountType = 'Public' AND PRSId IS NOT NULL AND StoreId IS NULL AND OfficialId IS NULL) OR (AccountType = 'Merchant' AND StoreId IS NOT NULL AND PRSId IS NULL AND OfficialId IS NULL) OR (AccountType = 'Official' AND OfficialId IS NOT NULL AND PRSId IS NULL AND StoreId IS NULL))
);
GO

-- RBAC role, e.g. Citizen, StoreOperator, VaccinationVerifier, IdentityOfficer, Auditor.
CREATE TABLE dbo.Role (
    RoleId INT IDENTITY(1,1) NOT NULL,
    RoleName VARCHAR(50) NOT NULL CONSTRAINT UQ_Role_RoleName UNIQUE,
    Description NVARCHAR(255) NULL,
    CONSTRAINT PK_Role PRIMARY KEY (RoleId)
);
GO

-- Fine-grained permission, e.g. DECRYPT_NATIONAL_ID, VERIFY_VACCINATION, SET_PURCHASE_LIMIT.
CREATE TABLE dbo.Permission (
    PermissionId INT IDENTITY(1,1) NOT NULL,
    PermissionCode VARCHAR(50) NOT NULL CONSTRAINT UQ_Permission_PermissionCode UNIQUE,
    Description NVARCHAR(255) NULL,
    CONSTRAINT PK_Permission PRIMARY KEY (PermissionId)
);
GO

-- Junction table resolving UserAccount M:N Role.
CREATE TABLE dbo.UserRole (
    UserId INT NOT NULL,
    RoleId INT NOT NULL,
    AssignedAt DATETIME2 NOT NULL CONSTRAINT DF_UserRole_AssignedAt DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_UserRole PRIMARY KEY (UserId, RoleId),
    CONSTRAINT FK_UserRole_UserId FOREIGN KEY (UserId) REFERENCES dbo.UserAccount(UserId),
    CONSTRAINT FK_UserRole_RoleId FOREIGN KEY (RoleId) REFERENCES dbo.Role(RoleId)
);
GO

-- Junction table resolving Role M:N Permission.
CREATE TABLE dbo.RolePermission (
    RoleId INT NOT NULL,
    PermissionId INT NOT NULL,
    CONSTRAINT PK_RolePermission PRIMARY KEY (RoleId, PermissionId),
    CONSTRAINT FK_RolePermission_RoleId FOREIGN KEY (RoleId) REFERENCES dbo.Role(RoleId),
    CONSTRAINT FK_RolePermission_PermissionId FOREIGN KEY (PermissionId) REFERENCES dbo.Permission(PermissionId)
);
GO

-- Restricted grocery or medical item (face mask, 4-litre milk, testing kit).
CREATE TABLE dbo.CriticalItem (
    ItemId INT IDENTITY(1,1) NOT NULL,
    ItemName NVARCHAR(100) NOT NULL CONSTRAINT UQ_CriticalItem_ItemName UNIQUE,
    Category VARCHAR(10) NOT NULL CONSTRAINT CK_CriticalItem_Category CHECK (Category IN ('Grocery','Medical')),
    UnitOfMeasure NVARCHAR(40) NOT NULL,
    CONSTRAINT PK_CriticalItem PRIMARY KEY (ItemId)
);
GO

-- Associative entity Store x CriticalItem holding the current quantity on hand.
CREATE TABLE dbo.StockLevel (
    StoreId INT NOT NULL,
    ItemId INT NOT NULL,
    QuantityAvailable INT NOT NULL CONSTRAINT CK_StockLevel_QuantityAvailable CHECK (QuantityAvailable >= 0),
    LastUpdatedAt DATETIME2 NOT NULL CONSTRAINT DF_StockLevel_LastUpdatedAt DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_StockLevel PRIMARY KEY (StoreId, ItemId),
    CONSTRAINT FK_StockLevel_StoreId FOREIGN KEY (StoreId) REFERENCES dbo.Store(StoreId),
    CONSTRAINT FK_StockLevel_ItemId FOREIGN KEY (ItemId) REFERENCES dbo.CriticalItem(ItemId)
);
GO

-- Government rule: max quantity of an item per person per day or week.
CREATE TABLE dbo.PurchaseLimit (
    LimitId INT IDENTITY(1,1) NOT NULL,
    ItemId INT NOT NULL,
    MaxQuantity INT NOT NULL CONSTRAINT CK_PurchaseLimit_MaxQuantity CHECK (MaxQuantity > 0),
    PeriodType VARCHAR(5) NOT NULL CONSTRAINT CK_PurchaseLimit_PeriodType CHECK (PeriodType IN ('Day','Week')),
    EffectiveFrom DATE NOT NULL,
    EffectiveTo DATE NULL,
    SetByOfficialId INT NOT NULL,
    CONSTRAINT PK_PurchaseLimit PRIMARY KEY (LimitId),
    CONSTRAINT FK_PurchaseLimit_ItemId FOREIGN KEY (ItemId) REFERENCES dbo.CriticalItem(ItemId),
    CONSTRAINT FK_PurchaseLimit_SetByOfficialId FOREIGN KEY (SetByOfficialId) REFERENCES dbo.GovernmentOfficial(OfficialId),
    CONSTRAINT CK_PurchaseLimit_1 CHECK (EffectiveTo IS NULL OR EffectiveTo >= EffectiveFrom)
);
GO

-- Government rule: people whose birth year ends in BirthYearDigit may buy the item on AllowedDayOfWeek.
CREATE TABLE dbo.PurchaseSchedule (
    ScheduleId INT IDENTITY(1,1) NOT NULL,
    ItemId INT NOT NULL,
    BirthYearDigit TINYINT NOT NULL CONSTRAINT CK_PurchaseSchedule_BirthYearDigit CHECK (BirthYearDigit BETWEEN 0 AND 9),
    AllowedDayOfWeek TINYINT NOT NULL CONSTRAINT CK_PurchaseSchedule_AllowedDayOfWeek CHECK (AllowedDayOfWeek BETWEEN 1 AND 7),
    EffectiveFrom DATE NOT NULL,
    EffectiveTo DATE NULL,
    SetByOfficialId INT NOT NULL,
    CONSTRAINT PK_PurchaseSchedule PRIMARY KEY (ScheduleId),
    CONSTRAINT FK_PurchaseSchedule_ItemId FOREIGN KEY (ItemId) REFERENCES dbo.CriticalItem(ItemId),
    CONSTRAINT FK_PurchaseSchedule_SetByOfficialId FOREIGN KEY (SetByOfficialId) REFERENCES dbo.GovernmentOfficial(OfficialId),
    CONSTRAINT UQ_PurchaseSchedule_1 UNIQUE (ItemId, BirthYearDigit, AllowedDayOfWeek, EffectiveFrom),
    CONSTRAINT CK_PurchaseSchedule_1 CHECK (EffectiveTo IS NULL OR EffectiveTo >= EffectiveFrom)
);
GO

-- A sale of restricted items to one person at one store.
CREATE TABLE dbo.Purchase (
    PurchaseId BIGINT IDENTITY(1,1) NOT NULL,
    PRSId CHAR(12) NOT NULL,
    StoreId INT NOT NULL,
    PurchasedAt DATETIME2 NOT NULL CONSTRAINT DF_Purchase_PurchasedAt DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_Purchase PRIMARY KEY (PurchaseId),
    CONSTRAINT FK_Purchase_PRSId FOREIGN KEY (PRSId) REFERENCES dbo.Person(PRSId),
    CONSTRAINT FK_Purchase_StoreId FOREIGN KEY (StoreId) REFERENCES dbo.Store(StoreId)
);
GO

-- Associative entity Purchase x CriticalItem with the quantity bought.
CREATE TABLE dbo.PurchaseLine (
    PurchaseId BIGINT NOT NULL,
    ItemId INT NOT NULL,
    Quantity INT NOT NULL CONSTRAINT CK_PurchaseLine_Quantity CHECK (Quantity > 0),
    CONSTRAINT PK_PurchaseLine PRIMARY KEY (PurchaseId, ItemId),
    CONSTRAINT FK_PurchaseLine_PurchaseId FOREIGN KEY (PurchaseId) REFERENCES dbo.Purchase(PurchaseId),
    CONSTRAINT FK_PurchaseLine_ItemId FOREIGN KEY (ItemId) REFERENCES dbo.CriticalItem(ItemId)
);
GO

-- Raised when an individual or business breaks a purchase limit or schedule.
CREATE TABLE dbo.Alert (
    AlertId BIGINT IDENTITY(1,1) NOT NULL,
    AlertType VARCHAR(25) NOT NULL CONSTRAINT CK_Alert_AlertType CHECK (AlertType IN ('LimitBreach','ScheduleBreach','MerchantNonCompliance')),
    PRSId CHAR(12) NULL,
    StoreId INT NULL,
    PurchaseId BIGINT NULL,
    LimitId INT NULL,
    ScheduleId INT NULL,
    RaisedAt DATETIME2 NOT NULL CONSTRAINT DF_Alert_RaisedAt DEFAULT (SYSUTCDATETIME()),
    Status VARCHAR(12) NOT NULL CONSTRAINT DF_Alert_Status DEFAULT ('Open') CONSTRAINT CK_Alert_Status CHECK (Status IN ('Open','UnderReview','Closed')),
    ReviewedByOfficialId INT NULL,
    CONSTRAINT PK_Alert PRIMARY KEY (AlertId),
    CONSTRAINT FK_Alert_PRSId FOREIGN KEY (PRSId) REFERENCES dbo.Person(PRSId),
    CONSTRAINT FK_Alert_StoreId FOREIGN KEY (StoreId) REFERENCES dbo.Store(StoreId),
    CONSTRAINT FK_Alert_PurchaseId FOREIGN KEY (PurchaseId) REFERENCES dbo.Purchase(PurchaseId),
    CONSTRAINT FK_Alert_LimitId FOREIGN KEY (LimitId) REFERENCES dbo.PurchaseLimit(LimitId),
    CONSTRAINT FK_Alert_ScheduleId FOREIGN KEY (ScheduleId) REFERENCES dbo.PurchaseSchedule(ScheduleId),
    CONSTRAINT FK_Alert_ReviewedByOfficialId FOREIGN KEY (ReviewedByOfficialId) REFERENCES dbo.GovernmentOfficial(OfficialId),
    CONSTRAINT CK_Alert_1 CHECK (PRSId IS NOT NULL OR StoreId IS NOT NULL)
);
GO

-- Vaccine product, keyed by its SNOMED CT product code (as used in FHIR vaccineCode).
CREATE TABLE dbo.Vaccine (
    VaccineCode VARCHAR(20) NOT NULL,
    VaccineName NVARCHAR(300) NOT NULL,
    Manufacturer NVARCHAR(100) NOT NULL,
    TargetDisease NVARCHAR(100) NOT NULL,
    CONSTRAINT PK_Vaccine PRIMARY KEY (VaccineCode)
);
GO

-- Official policy per vaccine and dose: minimum interval and validity period.
CREATE TABLE dbo.VaccinationPolicy (
    PolicyId INT IDENTITY(1,1) NOT NULL,
    VaccineCode VARCHAR(20) NOT NULL,
    DoseNumber TINYINT NOT NULL CONSTRAINT CK_VaccinationPolicy_DoseNumber CHECK (DoseNumber >= 1),
    MinDaysAfterPreviousDose SMALLINT NULL,
    ValidForDays SMALLINT NULL,
    EffectiveFrom DATE NOT NULL,
    EffectiveTo DATE NULL,
    SetByOfficialId INT NOT NULL,
    CONSTRAINT PK_VaccinationPolicy PRIMARY KEY (PolicyId),
    CONSTRAINT FK_VaccinationPolicy_VaccineCode FOREIGN KEY (VaccineCode) REFERENCES dbo.Vaccine(VaccineCode),
    CONSTRAINT FK_VaccinationPolicy_SetByOfficialId FOREIGN KEY (SetByOfficialId) REFERENCES dbo.GovernmentOfficial(OfficialId),
    CONSTRAINT UQ_VaccinationPolicy_1 UNIQUE (VaccineCode, DoseNumber, EffectiveFrom)
);
GO

-- One administered dose for one person, extracted from a FHIR upload or keyed in from a PDF.
CREATE TABLE dbo.VaccinationRecord (
    VaccinationRecordId BIGINT IDENTITY(1,1) NOT NULL,
    PRSId CHAR(12) NOT NULL,
    VaccineCode VARCHAR(20) NOT NULL,
    DoseNumber TINYINT NOT NULL CONSTRAINT CK_VaccinationRecord_DoseNumber CHECK (DoseNumber >= 1),
    OccurrenceDateTime DATETIME2 NOT NULL,
    LotNumber VARCHAR(30) NULL,
    AdministeredBy NVARCHAR(150) NULL,
    CountryCode CHAR(2) NOT NULL,
    SourceType VARCHAR(10) NOT NULL CONSTRAINT CK_VaccinationRecord_SourceType CHECK (SourceType IN ('FHIR','PDF','Manual')),
    SourceResourceId VARCHAR(64) NULL,
    UploadId CHAR(24) NULL,
    PolicyId INT NULL,
    VerificationStatus VARCHAR(10) NOT NULL CONSTRAINT DF_VaccinationRecord_VerificationStatus DEFAULT ('Pending') CONSTRAINT CK_VaccinationRecord_VerificationStatus CHECK (VerificationStatus IN ('Pending','Verified','Rejected')),
    CONSTRAINT PK_VaccinationRecord PRIMARY KEY (VaccinationRecordId),
    CONSTRAINT FK_VaccinationRecord_PRSId FOREIGN KEY (PRSId) REFERENCES dbo.Person(PRSId),
    CONSTRAINT FK_VaccinationRecord_VaccineCode FOREIGN KEY (VaccineCode) REFERENCES dbo.Vaccine(VaccineCode),
    CONSTRAINT FK_VaccinationRecord_PolicyId FOREIGN KEY (PolicyId) REFERENCES dbo.VaccinationPolicy(PolicyId)
);
GO

-- History of official checks on a vaccination record (who, how, outcome).
CREATE TABLE dbo.Verification (
    VerificationId BIGINT IDENTITY(1,1) NOT NULL,
    VaccinationRecordId BIGINT NOT NULL,
    OfficialId INT NOT NULL,
    Method VARCHAR(20) NOT NULL CONSTRAINT CK_Verification_Method CHECK (Method IN ('IssuerLookup','DocumentReview','FHIRSourceMatch')),
    Outcome VARCHAR(10) NOT NULL CONSTRAINT CK_Verification_Outcome CHECK (Outcome IN ('Verified','Rejected','NeedsInfo')),
    Notes NVARCHAR(500) NULL,
    VerifiedAt DATETIME2 NOT NULL CONSTRAINT DF_Verification_VerifiedAt DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_Verification PRIMARY KEY (VerificationId),
    CONSTRAINT FK_Verification_VaccinationRecordId FOREIGN KEY (VaccinationRecordId) REFERENCES dbo.VaccinationRecord(VaccinationRecordId),
    CONSTRAINT FK_Verification_OfficialId FOREIGN KEY (OfficialId) REFERENCES dbo.GovernmentOfficial(OfficialId)
);
GO

-- A traveller's check at a port of entry using their identifier and vaccination status.
CREATE TABLE dbo.BorderCheck (
    BorderCheckId BIGINT IDENTITY(1,1) NOT NULL,
    PRSId CHAR(12) NOT NULL,
    NationalIdentifierId INT NOT NULL,
    OfficialId INT NOT NULL,
    PortOfEntry NVARCHAR(100) NOT NULL,
    CheckedAt DATETIME2 NOT NULL CONSTRAINT DF_BorderCheck_CheckedAt DEFAULT (SYSUTCDATETIME()),
    Outcome VARCHAR(12) NOT NULL CONSTRAINT CK_BorderCheck_Outcome CHECK (Outcome IN ('Cleared','Quarantine','Refused')),
    CONSTRAINT PK_BorderCheck PRIMARY KEY (BorderCheckId),
    CONSTRAINT FK_BorderCheck_PRSId FOREIGN KEY (PRSId) REFERENCES dbo.Person(PRSId),
    CONSTRAINT FK_BorderCheck_NationalIdentifierId FOREIGN KEY (NationalIdentifierId) REFERENCES dbo.NationalIdentifier(NationalIdentifierId),
    CONSTRAINT FK_BorderCheck_OfficialId FOREIGN KEY (OfficialId) REFERENCES dbo.GovernmentOfficial(OfficialId)
);
GO

-- Supporting indexes ------------------------------------------------
CREATE INDEX IX_NationalIdentifier_PRSId ON dbo.NationalIdentifier(PRSId);
CREATE INDEX IX_NationalIdentifier_IdentifierTypeCode ON dbo.NationalIdentifier(IdentifierTypeCode);
CREATE INDEX IX_FamilyLink_DependentPRSId ON dbo.FamilyLink(DependentPRSId);
CREATE INDEX IX_Merchant_VerifiedByOfficialId ON dbo.Merchant(VerifiedByOfficialId);
CREATE INDEX IX_Store_MerchantId ON dbo.Store(MerchantId);
CREATE INDEX IX_UserAccount_PRSId ON dbo.UserAccount(PRSId);
CREATE INDEX IX_UserAccount_StoreId ON dbo.UserAccount(StoreId);
CREATE INDEX IX_UserAccount_OfficialId ON dbo.UserAccount(OfficialId);
CREATE UNIQUE INDEX UX_UserAccount_PRSId ON dbo.UserAccount(PRSId) WHERE PRSId IS NOT NULL;
CREATE UNIQUE INDEX UX_UserAccount_OfficialId ON dbo.UserAccount(OfficialId) WHERE OfficialId IS NOT NULL;
CREATE INDEX IX_UserRole_RoleId ON dbo.UserRole(RoleId);
CREATE INDEX IX_RolePermission_PermissionId ON dbo.RolePermission(PermissionId);
CREATE INDEX IX_StockLevel_ItemId ON dbo.StockLevel(ItemId);
CREATE INDEX IX_PurchaseLimit_ItemId ON dbo.PurchaseLimit(ItemId);
CREATE INDEX IX_PurchaseLimit_SetByOfficialId ON dbo.PurchaseLimit(SetByOfficialId);
CREATE INDEX IX_PurchaseSchedule_ItemId ON dbo.PurchaseSchedule(ItemId);
CREATE INDEX IX_PurchaseSchedule_SetByOfficialId ON dbo.PurchaseSchedule(SetByOfficialId);
CREATE INDEX IX_Purchase_PRSId ON dbo.Purchase(PRSId);
CREATE INDEX IX_Purchase_StoreId ON dbo.Purchase(StoreId);
CREATE INDEX IX_PurchaseLine_ItemId ON dbo.PurchaseLine(ItemId);
CREATE INDEX IX_Alert_PRSId ON dbo.Alert(PRSId);
CREATE INDEX IX_Alert_StoreId ON dbo.Alert(StoreId);
CREATE INDEX IX_Alert_PurchaseId ON dbo.Alert(PurchaseId);
CREATE INDEX IX_Alert_LimitId ON dbo.Alert(LimitId);
CREATE INDEX IX_Alert_ScheduleId ON dbo.Alert(ScheduleId);
CREATE INDEX IX_Alert_ReviewedByOfficialId ON dbo.Alert(ReviewedByOfficialId);
CREATE INDEX IX_VaccinationPolicy_VaccineCode ON dbo.VaccinationPolicy(VaccineCode);
CREATE INDEX IX_VaccinationPolicy_SetByOfficialId ON dbo.VaccinationPolicy(SetByOfficialId);
CREATE INDEX IX_VaccinationRecord_PRSId ON dbo.VaccinationRecord(PRSId);
CREATE INDEX IX_VaccinationRecord_VaccineCode ON dbo.VaccinationRecord(VaccineCode);
CREATE INDEX IX_VaccinationRecord_PolicyId ON dbo.VaccinationRecord(PolicyId);
CREATE UNIQUE INDEX UX_VaccinationRecord_PRSId_SourceResourceId ON dbo.VaccinationRecord(PRSId, SourceResourceId) WHERE SourceResourceId IS NOT NULL;
CREATE INDEX IX_Verification_VaccinationRecordId ON dbo.Verification(VaccinationRecordId);
CREATE INDEX IX_Verification_OfficialId ON dbo.Verification(OfficialId);
CREATE INDEX IX_BorderCheck_PRSId ON dbo.BorderCheck(PRSId);
CREATE INDEX IX_BorderCheck_NationalIdentifierId ON dbo.BorderCheck(NationalIdentifierId);
CREATE INDEX IX_BorderCheck_OfficialId ON dbo.BorderCheck(OfficialId);
CREATE INDEX IX_Purchase_PRSId_PurchasedAt ON dbo.Purchase(PRSId, PurchasedAt);
CREATE SPATIAL INDEX SX_Store_GeoLocation ON dbo.Store(GeoLocation);
GO

/* =====================================================================
   Reference / demo data (values taken from the scenario)
   ===================================================================== */
INSERT INTO dbo.IdentifierType (IdentifierTypeCode, TypeName, IssuingAuthority) VALUES
 ('PASSPORT',        N'Passport',                     N'Passport issuing authority of IssuingCountryCode'),
 ('DRIVING_LICENCE', N'Driving Licence Number',       N'DVLA or foreign equivalent'),
 ('BRP',             N'Biometric Residence Permit',   N'UK Home Office'),
 ('NHS_NUMBER',      N'NHS Number',                   N'NHS England');

INSERT INTO dbo.Role (RoleName, Description) VALUES
 ('Citizen',             N'Member of the public: own and dependants'' data only'),
 ('StoreOperator',       N'Merchant store account: purchases and stock'),
 ('PolicyOfficer',       N'Sets purchase limits, schedules and vaccination policy'),
 ('VaccinationVerifier', N'Validates uploaded vaccination records'),
 ('IdentityOfficer',     N'May decrypt national identifiers and DOB'),
 ('BorderOfficer',       N'Performs border checks'),
 ('Auditor',             N'Read-only access to audit logs');

INSERT INTO dbo.Permission (PermissionCode, Description) VALUES
 ('VIEW_OWN_RECORD',       N'View own profile and dependants'),
 ('ENROL_DEPENDANT',       N'Enrol a child under 18'),
 ('UPLOAD_VACCINATION',    N'Upload FHIR or PDF vaccination evidence'),
 ('CHECK_ELIGIBILITY',     N'Check whether a person may buy an item now'),
 ('RECORD_PURCHASE',       N'Record a sale of a critical item'),
 ('UPDATE_STOCK',          N'Update stock levels for a store'),
 ('SET_PURCHASE_RULES',    N'Create purchase limits and schedules'),
 ('VERIFY_MERCHANT',       N'Approve merchant enrolment'),
 ('VERIFY_VACCINATION',    N'Verify or reject vaccination records'),
 ('DECRYPT_NATIONAL_ID',   N'Decrypt NationalIdentifier.IdentifierValue'),
 ('DECRYPT_DOB',           N'Decrypt Person.DateOfBirth'),
 ('CONDUCT_BORDER_CHECK',  N'Record a border check'),
 ('VIEW_AUDIT_LOG',        N'Read the audit log');

INSERT INTO dbo.RolePermission (RoleId, PermissionId)
SELECT r.RoleId, p.PermissionId
FROM (VALUES
 ('Citizen','VIEW_OWN_RECORD'), ('Citizen','ENROL_DEPENDANT'), ('Citizen','UPLOAD_VACCINATION'),
 ('StoreOperator','CHECK_ELIGIBILITY'), ('StoreOperator','RECORD_PURCHASE'), ('StoreOperator','UPDATE_STOCK'),
 ('PolicyOfficer','SET_PURCHASE_RULES'), ('PolicyOfficer','VERIFY_MERCHANT'),
 ('VaccinationVerifier','VERIFY_VACCINATION'), ('VaccinationVerifier','DECRYPT_DOB'),
 ('IdentityOfficer','DECRYPT_NATIONAL_ID'), ('IdentityOfficer','DECRYPT_DOB'),
 ('BorderOfficer','CONDUCT_BORDER_CHECK'), ('BorderOfficer','DECRYPT_NATIONAL_ID'),
 ('Auditor','VIEW_AUDIT_LOG')
) AS m(RoleName, PermissionCode)
JOIN dbo.Role r ON r.RoleName = m.RoleName
JOIN dbo.Permission p ON p.PermissionCode = m.PermissionCode;

INSERT INTO dbo.GovernmentOfficial (StaffNumber, FullName, Department, JobTitle, WorkEmail) VALUES
 ('GOV-0001', N'A. Official', N'Department of Health', N'Policy Officer', N'a.official@prs.gov.example');

INSERT INTO dbo.CriticalItem (ItemName, Category, UnitOfMeasure) VALUES
 (N'Face mask', 'Medical', N'single mask'),
 (N'Milk', 'Grocery', N'4-litre pack'),
 (N'COVID-19 testing kit', 'Medical', N'kit');

-- "one 4-litre milk pack per day", "no more than 7 face masks per week"
INSERT INTO dbo.PurchaseLimit (ItemId, MaxQuantity, PeriodType, EffectiveFrom, SetByOfficialId)
SELECT ItemId, q, p, '2026-01-01', 1
FROM (VALUES (N'Milk', 1, 'Day'), (N'Face mask', 7, 'Week'), (N'COVID-19 testing kit', 2, 'Week')) v(n, q, p)
JOIN dbo.CriticalItem ci ON ci.ItemName = v.n;

-- "born in years ending (0,2) buy masks on Monday, (1,3) on Tuesday, and so on"  (1 = Monday)
INSERT INTO dbo.PurchaseSchedule (ItemId, BirthYearDigit, AllowedDayOfWeek, EffectiveFrom, SetByOfficialId)
SELECT ci.ItemId, d.Digit, d.Dow, '2026-01-01', 1
FROM (VALUES (0,1),(2,1),(1,2),(3,2),(4,3),(6,3),(5,4),(7,4),(8,5),(9,5)) d(Digit, Dow)
CROSS JOIN dbo.CriticalItem ci WHERE ci.ItemName = N'Face mask';

INSERT INTO dbo.Vaccine (VaccineCode, VaccineName, Manufacturer, TargetDisease) VALUES
 ('39114911000001105',
  N'COVID-19 Vaccine AstraZeneca (ChAdOx1 S [recombinant]) 5x10,000,000,000 viral particles/0.5ml dose solution for injection multidose vials (AstraZeneca UK Ltd) (product)',
  N'AstraZeneca Ltd', N'COVID-19');

INSERT INTO dbo.VaccinationPolicy (VaccineCode, DoseNumber, MinDaysAfterPreviousDose, ValidForDays, EffectiveFrom, SetByOfficialId) VALUES
 ('39114911000001105', 1, NULL, 365, '2020-12-01', 1),
 ('39114911000001105', 2, 21,   365, '2020-12-01', 1);

-- Person from the NHS FHIR sample (NHS number 9000000009, born 1965-02-28)
INSERT INTO dbo.Person (FirstName, LastName, DateOfBirth, BirthYearDigit, ResidencyStatus, NationalityCode)
VALUES (N'Sample', N'Traveller', '1965-02-28', 5, 'Visitor', 'GB');
INSERT INTO dbo.NationalIdentifier (PRSId, IdentifierTypeCode, IdentifierValue, IssuingCountryCode, IsPrimary)
VALUES ('PRS000000001', 'NHS_NUMBER', N'9000000009', 'GB', 1);
INSERT INTO dbo.UserAccount (Username, PasswordHash, AccountType, PRSId)
VALUES (N'sample.traveller', HASHBYTES('SHA2_256', 'demo-only'), 'Public', 'PRS000000001');
INSERT INTO dbo.UserRole (UserId, RoleId) SELECT 1, RoleId FROM dbo.Role WHERE RoleName = 'Citizen';

INSERT INTO dbo.Merchant (BusinessLicenceNumber, BusinessName, BusinessType, RegisteredAddress, ContactEmail, EnrolmentStatus, VerifiedByOfficialId)
VALUES ('LIC-2026-000123', N'Corner Pharmacy Ltd', 'Pharmacy', N'1 High Street, Wolverhampton', N'ops@cornerpharmacy.example', 'Verified', 1);
INSERT INTO dbo.Store (MerchantId, StoreName, AddressLine, City, Postcode, GeoLocation) VALUES
 (1, N'Corner Pharmacy - City Centre', N'1 High Street', N'Wolverhampton', 'WV1 1AA', geography::Point(52.5862, -2.1288, 4326)),
 (1, N'Corner Pharmacy - Whitmore Reans', N'12 Avenue Road', N'Wolverhampton', 'WV3 9XX', geography::Point(52.5951, -2.1490, 4326));
INSERT INTO dbo.StockLevel (StoreId, ItemId, QuantityAvailable) VALUES (1, 1, 250), (1, 2, 40), (2, 1, 0), (2, 3, 15);
GO

/* =====================================================================
   Business rules expressed against the model
   ===================================================================== */

-- Monday = 1 ... Sunday = 7, independent of @@DATEFIRST (1900-01-01 was a Monday)
CREATE OR ALTER FUNCTION dbo.fn_IsoDayOfWeek (@d DATE) RETURNS TINYINT
AS BEGIN RETURN (DATEDIFF(DAY, '19000101', @d) % 7) + 1; END;
GO

-- Can this person buy @Quantity of @ItemId at @At?  (schedule by DOB + limit vs. purchase history)
CREATE OR ALTER PROCEDURE dbo.usp_CheckPurchaseEligibility
    @PRSId CHAR(12), @ItemId INT, @Quantity INT, @At DATETIME2 = NULL,
    @IsEligible BIT OUTPUT, @Reason NVARCHAR(200) OUTPUT, @LimitId INT = NULL OUTPUT, @ScheduleId INT = NULL OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    SET @At = COALESCE(@At, SYSUTCDATETIME());
    DECLARE @Day DATE = CAST(@At AS DATE);
    DECLARE @Dow TINYINT = dbo.fn_IsoDayOfWeek(@Day);
    DECLARE @Digit TINYINT = (SELECT BirthYearDigit FROM dbo.Person WHERE PRSId = @PRSId AND IsActive = 1);
    SELECT @IsEligible = 1, @Reason = N'Eligible', @LimitId = NULL, @ScheduleId = NULL;

    IF @Digit IS NULL BEGIN SELECT @IsEligible = 0, @Reason = N'Unknown or inactive PRS-Id'; RETURN; END;

    -- 1. Day-of-week schedule (only applies if the item has an active schedule)
    IF EXISTS (SELECT 1 FROM dbo.PurchaseSchedule s WHERE s.ItemId = @ItemId
               AND @Day BETWEEN s.EffectiveFrom AND COALESCE(s.EffectiveTo, '9999-12-31'))
       AND NOT EXISTS (SELECT 1 FROM dbo.PurchaseSchedule s WHERE s.ItemId = @ItemId
               AND s.BirthYearDigit = @Digit AND s.AllowedDayOfWeek = @Dow
               AND @Day BETWEEN s.EffectiveFrom AND COALESCE(s.EffectiveTo, '9999-12-31'))
    BEGIN
        SELECT TOP (1) @ScheduleId = s.ScheduleId FROM dbo.PurchaseSchedule s
        WHERE s.ItemId = @ItemId AND s.BirthYearDigit = @Digit
          AND @Day BETWEEN s.EffectiveFrom AND COALESCE(s.EffectiveTo, '9999-12-31');
        SELECT @IsEligible = 0, @Reason = N'Not an allowed day for this birth year';
        RETURN;
    END;

    -- 2. Quantity limit over the current day / ISO week
    DECLARE @Max INT, @Period VARCHAR(5), @From DATETIME2, @Bought INT;
    SELECT TOP (1) @LimitId = l.LimitId, @Max = l.MaxQuantity, @Period = l.PeriodType
    FROM dbo.PurchaseLimit l
    WHERE l.ItemId = @ItemId AND @Day BETWEEN l.EffectiveFrom AND COALESCE(l.EffectiveTo, '9999-12-31')
    ORDER BY l.EffectiveFrom DESC;

    IF @LimitId IS NOT NULL
    BEGIN
        SET @From = CASE @Period WHEN 'Day' THEN CAST(@Day AS DATETIME2)
                                 ELSE CAST(DATEADD(DAY, 1 - @Dow, @Day) AS DATETIME2) END;
        SELECT @Bought = COALESCE(SUM(pl.Quantity), 0)
        FROM dbo.Purchase p JOIN dbo.PurchaseLine pl ON pl.PurchaseId = p.PurchaseId
        WHERE p.PRSId = @PRSId AND pl.ItemId = @ItemId AND p.PurchasedAt >= @From AND p.PurchasedAt <= @At;

        IF @Bought + @Quantity > @Max
        BEGIN
            SELECT @IsEligible = 0,
                   @Reason = CONCAT(N'Limit ', @Max, N' per ', @Period, N' exceeded (already bought ', @Bought, N')');
            RETURN;
        END;
    END;
    SET @LimitId = NULL;
END;
GO

-- Record a single-item sale atomically: check eligibility, write purchase, decrement stock, or raise an alert.
CREATE OR ALTER PROCEDURE dbo.usp_RecordPurchase
    @PRSId CHAR(12), @StoreId INT, @ItemId INT, @Quantity INT, @At DATETIME2 = NULL
AS
BEGIN
    SET NOCOUNT ON; SET XACT_ABORT ON;
    SET @At = COALESCE(@At, SYSUTCDATETIME());
    DECLARE @ok BIT, @why NVARCHAR(200), @lim INT, @sch INT, @pid BIGINT;
    BEGIN TRANSACTION;
    EXEC dbo.usp_CheckPurchaseEligibility @PRSId, @ItemId, @Quantity, @At, @ok OUTPUT, @why OUTPUT, @lim OUTPUT, @sch OUTPUT;
    IF @ok = 0
    BEGIN
        INSERT INTO dbo.Alert (AlertType, PRSId, StoreId, LimitId, ScheduleId, RaisedAt)
        VALUES (CASE WHEN @sch IS NOT NULL THEN 'ScheduleBreach' ELSE 'LimitBreach' END, @PRSId, @StoreId, @lim, @sch, @At);
        COMMIT;
        SELECT CAST(0 AS BIT) AS Accepted, @why AS Reason;
        RETURN;
    END;
    UPDATE dbo.StockLevel SET QuantityAvailable = QuantityAvailable - @Quantity, LastUpdatedAt = SYSUTCDATETIME()
    WHERE StoreId = @StoreId AND ItemId = @ItemId AND QuantityAvailable >= @Quantity;
    IF @@ROWCOUNT = 0 BEGIN ROLLBACK; SELECT CAST(0 AS BIT) AS Accepted, N'Insufficient stock' AS Reason; RETURN; END;
    INSERT INTO dbo.Purchase (PRSId, StoreId, PurchasedAt) VALUES (@PRSId, @StoreId, @At);
    SET @pid = SCOPE_IDENTITY();
    INSERT INTO dbo.PurchaseLine (PurchaseId, ItemId, Quantity) VALUES (@pid, @ItemId, @Quantity);
    COMMIT;
    SELECT CAST(1 AS BIT) AS Accepted, N'Recorded' AS Reason, @pid AS PurchaseId;
END;
GO

-- Critical item locator: nearest open stores with stock of an item.
CREATE OR ALTER PROCEDURE dbo.usp_FindNearestStock @Latitude FLOAT, @Longitude FLOAT, @ItemId INT, @Top INT = 5
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @here GEOGRAPHY = geography::Point(@Latitude, @Longitude, 4326);
    SELECT TOP (@Top) s.StoreId, s.StoreName, s.Postcode, sl.QuantityAvailable,
           CAST(s.GeoLocation.STDistance(@here) / 1000.0 AS DECIMAL(8,2)) AS DistanceKm
    FROM dbo.Store s JOIN dbo.StockLevel sl ON sl.StoreId = s.StoreId
    WHERE sl.ItemId = @ItemId AND sl.QuantityAvailable > 0 AND s.IsOpen = 1
    ORDER BY s.GeoLocation.STDistance(@here);
END;
GO

-- Vaccination compliance per dose: record matched to the policy for that vaccine and dose.
CREATE OR ALTER VIEW dbo.vw_VaccinationCompliance AS
SELECT vr.PRSId, vr.VaccinationRecordId, vr.VaccineCode, vr.DoseNumber, vr.OccurrenceDateTime,
       vr.VerificationStatus, vp.PolicyId,
       DATEADD(DAY, vp.ValidForDays, CAST(vr.OccurrenceDateTime AS DATE)) AS ValidUntil,
       CASE WHEN vr.VerificationStatus = 'Verified' AND vp.PolicyId IS NOT NULL
             AND (vp.ValidForDays IS NULL OR DATEADD(DAY, vp.ValidForDays, CAST(vr.OccurrenceDateTime AS DATE)) >= CAST(SYSUTCDATETIME() AS DATE))
            THEN 'Compliant' ELSE 'NotCompliant' END AS ComplianceStatus
FROM dbo.VaccinationRecord vr
LEFT JOIN dbo.VaccinationPolicy vp ON vp.PolicyId = vr.PolicyId;
GO
