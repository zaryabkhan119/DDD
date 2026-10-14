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
