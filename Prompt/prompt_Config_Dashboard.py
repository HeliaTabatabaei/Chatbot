SCHEMA = """

Database schema for generating SQL queries from Persian questions.

--------------------------------------------------
View name: ai_request_analysis
--------------------------------------------------

Description:
Service requests for devices located in offices (دفاتر).
Each row represents one service request (خرابی / سرویس).

Columns:

Requests_Id (int)
Unique identifier of the service request.

DeviceTerminal (string)
Terminal number of the device.

DeviceId (int)
Unique device identifier.

AreaTitle (string)
Office name (دفتر). Each device belongs to an office.
Example values: تهران مرکز، تهران غرب، مشهد، اصفهان.

Area_Id (smallint)

BrandModelTypeTitle (string)
Full model title of the device.

Brand (string)
Device brand.

Type (string)
Device type.
Device Type / نوع دستگاه normalization:

اگر سؤال کاربر شامل نوع دستگاه بود، آن را به یکی از مقادیر زیر نگاشت کن:

ATM
- فارسی: خودپرداز
- انگلیسی: ATM

CRS
- فارسی: سی‌آر‌اس، CRS
- انگلیسی: CRS

Cash Acceptor
- فارسی: پذیرش‌کننده وجه، اسکناس‌پذیر، پول‌پذیر، دستگاه دریافت وجه
- انگلیسی: Cash Acceptor

Kiosk
- فارسی: کیوسک
- انگلیسی: Kiosk

Scanner
- فارسی: اسکنر
- انگلیسی: Scanner

MultiMedia
- فارسی: مالتی‌مدیا، چندرسانه‌ای
- انگلیسی: MultiMedia / Multimedia

قانون:
اگر کاربر هر کدام از این واژه‌ها را به فارسی یا انگلیسی نوشت، باید آن را به همان نوع دستگاه تبدیل کنی و در فیلتر SQL استفاده کنی.
InsertedDate (int)
Request creation date in Persian format YYYYMMDD.

InsertedTime (string)
Request creation time.

RequestDeadLineDate (int)
Deadline date for completing the request (Persian YYYYMMDD).

RequestDeadLineTime (string)
Deadline time.

EndDate (int)
Date when the request was completed.

EndTime (string)
Completion time.

DelayMinute (int)
Delay minutes between deadline and completion.

DelayMinuteWithCalculateOff (int)
Delay minutes calculated using internal rules.

DelayReasonID (int)
Identifier of delay reason.

DelayReasonTitle (string)
Title of delay reason.

IsCancel (int)
Indicates if request is cancelled.
0 = not cancelled
1 = cancelled

CancelReasonTitle (string)
Reason for cancellation.

ServiceID (int)
Service identifier.

RepeatRequest_Id (int)
Identifier of repeat failure request.

TitleRepeatRequest (string)
Reason or title of repeat failure.

PersonelId (string)
ID of the expert/technician responsible for the service request.

FullName (string)
Neme of the expert/technician responsible for the service request.

Usage:
Use this view when the question asks about:
- number of failures (خرابی)
- service requests
- delay statistics
- cancelled requests

Usually cancelled requests should be excluded using:
IsCancel = 0

--------------------------------------------------
View name: ai_GetDeviceCount
--------------------------------------------------

Description:
Contains the list of devices installed in offices.
Each row represents one device.

Columns:

DeviceID (int)
Unique device identifier.

DeviceSerial (string)
Device serial number.

AreaId (int)
Office identifier.

ParentId (int)
Parent identifier.

AreaTitle (string)
Office name (دفتر).

Brand (string)
Device brand.

Brand : device brand (Wincor, NCR, ...)
DeviceType : type of device (ATM, CRS)
Type of device.

DeviceModelTitle (string)
Device model title.

Year (int)
Year.

Month (int)
Month.

FinanceYear (int)
Financial year.

StartDateMiladi (date)
Device activation date.

EndDateMiladi (date)
Device deactivation date.

Usage:
Use this view when the question asks about:
- number of devices
- device statistics
- number of devices in an office

To count devices use:

SELECT COUNT(Distinct DeviceID)
FROM ai_GetDeviceCount


--------------------------------------------------
View name: ai_CurrentDateContext
--------------------------------------------------

Description:
Contains dynamic current date context (both Persian/Shamsi and Gregorian) as well as relative references such as previous Persian year.
Always contains exactly one row representing the execution date.

Columns:

CurrentPersianDateKey (int)
Current Persian date as an 8-digit integer (e.g. 14050609). 
Use this for exact date matching with `InsertedDate` (e.g. for "امروز"  و"جاری").

CurrentPersianDate (nvarchar(4000))
Current Persian date as a formatted string (e.g. '1405/06/09').

CurrentPersianYear (int)
Current Persian year (e.g. 1405).

CurrentPersianMonth (nvarchar(2))
Current Persian month with 2 digits (e.g. '01', '06', '12').

CurrentPersianMonthName (nvarchar(8))
Current Persian month name (e.g. N'شهریور', N'مهر').

CurrentPersianDay (nvarchar(2))
Current Persian day of month with 2 digits (e.g. '01', '09', '31').

PreviousPersianYear (int)
Previous Persian year (e.g. 1404). 
Use this when the user asks for "پارسال", " گذشتهسال", or relative .

CurrentGregorianDate (date)
Current Gregorian date (e.g. '2026-08-31').

CurrentGregorianYear (int)
Current Gregorian year (e.g. 2026).

CurrentGregorianMonth (varchar(2))
Current Gregorian month (e.g. '08').

CurrentGregorianDay (varchar(2))
Current Gregorian day of month (e.g. '31').

Usage:
Use this view whenever the question includes relative date terms:
- "امروز"/"روز جاری" (Today): use `CurrentPersianDateKey`
- "امسال"/"سال جاری" (This Year): use `CurrentPersianYear`
- "ماه جاری" (This Month): use `CurrentPersianYear` and `CurrentPersianMonth`
- "سال گذشته" / "پارسال"  (Last Year): use `PreviousPersianYear`
- Year-over-Year (YoY) / MTD comparisons for past year

Important:
Never hardcode current or previous years when relative words are present. Query this view instead:

SELECT 
    @PrevYear = PreviousPersianYear,
    @CurMonth = CAST(CurrentPersianMonth AS INT),
    @CurDay   = CAST(CurrentPersianDay AS INT)
FROM dbo.ai_CurrentDateContext;


--------------------------------------------------
Important SQL generation rules
--------------------------------------------------

1. Office name filtering

Users may type partial or incomplete office names.

Never use equality (=) for AreaTitle.

Always use LIKE with wildcards.

Correct filter example:

AreaTitle LIKE N'%تهران%'

Example:

User question:
تعداد خرابی در دفتر تهران

SQL condition:
WHERE AreaTitle LIKE N'%تهران%'

--------------------------------------------------

2. Device count queries

When the user asks about number of devices,
ALWAYS use the view:

ai_GetDeviceCount

Example:

SELECT COUNT(Distinct DeviceID)
FROM ai_GetDeviceCount
WHERE AreaTitle LIKE N'%تهران%'

--------------------------------------------------

3. Failure or request count

When the user asks about failures, service requests, or خرابی,
use the view:

ai_request_analysis

Example:

SELECT COUNT(Requests_Id)
FROM ai_request_analysis
WHERE AreaTitle LIKE N'%تهران%'
AND IsCancel = 0

--------------------------------------------------
If the question contains a device type(نوع تجهیز) (ATM, CRS, ...),
filter:
Type in ai_request_analysis
AND
DeviceType in ai_GetDeviceCount
and Wincor estcom .. are Brand(برند)
SQL safety rules

Only generate SELECT queries.
Do not generate INSERT, UPDATE, DELETE, DROP, or ALTER statements.

Return only the SQL query without explanation.



"""


############################## نرخ خرابی/تعداد خرابی/ تعداد دستگاه/ میانگین تاخیر/دلایل تکرار خرابی
METRICS = """
================================================================
CRITICAL RULE: OFFICE & SATELLITES FILTERING
================================================================
- Device Aggregation Rule: ALWAYS use COUNT(DISTINCT DeviceID). NEVER write COUNT(DeviceID) without DISTINCT.
- Request Aggregation Rule: ALWAYS use COUNT(DISTINCT Requests_Id). NEVER write COUNT(Requests_Id) without DISTINCT.
All office information is available in `ai_request_analysis`.

Columns:
- `AreaTitle` = office name
- `Area_Id` = ID of that same office
- `ParentId` = ID of its parent office

When the user asks about an office:

1. Find the requested office by `AreaTitle` and get its `Area_Id`
   from `ai_request_analysis`.

2. NEVER guess or hard-code the `Area_Id`.

3. For all calculations, include:
   - records where `Area_Id` equals the requested office's `Area_Id`
   - records where `ParentId` equals the requested office's `Area_Id`

Therefore:

Requested Office
+
All its child/satellite offices

must be included.

Example:
If the user asks for "دفتر ارومیه":
- First find the `Area_Id` of "دفتر ارومیه".
- Then include ارومیه itself.
- Also include every office whose `ParentId` equals ارومیه's `Area_Id`.
- Therefore, if دفتر خوی has that `ParentId`, دفتر خوی must also be included.

IMPORTANT:
- `Area_Id` belongs to the `AreaTitle` in the same record.
- `ParentId` is the ID of that office's parent.
- NEVER use `AreaTitle LIKE` to find satellite offices.
- NEVER reuse an Area_Id from another office or from an example.
- If the user explicitly asks for "فقط خود دفتر", do not include satellites.
================================================================
CRITICAL DATE & TIMEFRAME RULES (قوانین یکپارچه و جامع تاریخ)
================================================================
همیشه اطلاعات پایه تقویم را فقط و فقط از ویوی dbo.ai_CurrentDateContext بخوانید. هرگز سال یا تاریخ را هاردکد نکنید.

بازه زمانی بر اساس درخواست کاربر دقیقاً طبق یکی از ۴ حالت زیر تعیین می‌شود:

۱. ماه سپری‌شده در سال جاری یا سال‌های گذشته (مانند "خرداد سال جاری"، "اردیبهشت ۱۴۰۴"):
   - تاریخ شروع: روز اول همان ماه (مثلاً YYYY0301)
   - تاریخ پایان: آخرین روز همان ماه بر اساس تقویم شمسی (روز ۳۱ برای ماه‌های ۰۱ تا ۰۶ | روز ۳۰ برای ماه‌های ۰۷ تا ۱۱ | روز ۲۹ یا ۳۰ برای ماه ۱۲)
   - خروجی: یک بازه کامل از روز ۱ تا آخر ماه.

۲. ماه جاری فعال (ماهی که اکنون در آن هستیم و هنوز تمام نشده است):
   - تاریخ شروع: روز اول ماه جاری (مثلاً CurrentPersianYear + CurrentPersianMonth + '01')
   - تاریخ پایان: تاریخ دقیق روز جاری یعنی CurrentPersianDate (بازه MTD تا امروز).

================================================================
۳. همان ماه جاری در سال گذشته (مقایسه هم‌دوره YoY - مانند "شهریور سال گذشته/پارسال"):
================================================================
================================================================
قانون مقایسه هم‌دوره سال گذشته (YoY / همان ماه جاری در سال قبل):
================================================================
هنگامی که کاربر آماری برای ماهی از سال گذشته درخواست می‌کند که دقیقاً با ماه جاری برابر است (مثلاً در شهریور بگوید «شهریور پارسال»):

۱. الزامات کوئری SQL:
   - بازه تاریخ WHERE باید از اول ماه تا انتهای ماه سال قبل باشد (@StartDate تا @EndDateFull).
   - باید همزمان دو سری ستون در یک SELECT خروجی داده شود:
     الف) ستون‌های MTD (تا تاریخ معادل امروز در سال قبل): با شرط `InsertedDate <= @EndDateMTD`
     ب) ستون‌های کل ماه (Full Month): بدون شرط روز، برای کل داده‌های ماه.

۲. الزامات پاسخ نهایی کاربر (Answer):
   - مدل موظف است در متن پاسخ، هر دو گزارش را به تفکیک و شفاف بیان کند:
     * بخش اول: عملکرد تا روز معادل امروز (MTD).
     * بخش دوم: عملکرد کل ماه سپری‌شده.
================================================================

۴. سایر ماه‌های گذشته در سال قبل (مثلاً در شهریور بگوید "خرداد پارسال"):
   - فقط یک بازه کامل محاسبه می‌شود: از روز ۰۱ تا روز آخر همان ماه در PreviousPersianYear.

قوانین قطعی و الزامی تاریخ:
- متغیرهای بازه تاریخ شروع (@StartDate) و پایان (@EndDate) باید دقیقاً یکسان در تمام شروط (هم صورت و هم مخرج کسرها) اعمال شوند.
- هیچ بازه‌ای نباید بدون تاریخ پایان مشخص رها شود.
================================================================




================================================================
PERSIAN YEAR DATA LIMIT
================================================================

The minimum supported Persian year is 1404.

If the user requests Persian year 1403 or any earlier year:

- DO NOT generate SQL.
- DO NOT query ai_request_analysis.


Return only:
"اطلاعات فقط از سال 1404 به بعد در دسترس است."

Note:
For relative terms like "امروز", "ماه جاری", "امسال", "پارسال" or "سال گذشته", ALWAYS generate the SQL query using dbo.ai_CurrentDateContext.

================================================================
OFFICE RULE:
================================================================
- Find the requested office using AreaTitle LIKE N'%<requested office name>%'.
- Do NOT use AreaTitle = for resolving the requested office.
- MainAreaId = Area_Id of the matched office.
- Include:
  Area_Id = MainAreaId
  OR ParentId = MainAreaId
================================================================








Cancellation Rate (نرخ کنسلی):

Cancelled requests divided by total requests.

SQL logic:

SUM(CASE WHEN IsCancel = 1 THEN 1 ELSE 0 END) * 1.0
/
COUNT(Requests_Id)

Data source:
ai_request_analysis


Average Delay (میانگین تاخیر):

Average of DelayMinute.

SQL logic:

AVG(DelayMinute)

Data source:
ai_request_analysis


Max Delay (بیشترین تاخیر):

Maximum value of DelayMinute.

SQL logic:

MAX(DelayMinute)

Data source:
ai_request_analysis
================================================================
FAILURE & REPEAT FAILURE METRICS (تکرار خرابی)
================================================================
Data source: ai_request_analysis

COMMON RULES FOR ALL FAILURE METRICS:
- State filter: Always State_Id IN (1, 2, 5, 6, 7, 8, 9, 10, 11)
- IsCancel filter: Do NOT apply any IsCancel condition.
- Office & Date: Strictly follow OFFICE (Area_Id = @MainAreaId OR ParentId = @MainAreaId) and CRITICAL DATE & TIMEFRAME RULES.
- Aggregation: Always use COUNT(DISTINCT Requests_Id).

----------------------------------------------------------------
1. Total Failure Count (تعداد کل خرابی‌ها):
----------------------------------------------------------------
- Intent: User asks for "تعداد خرابی", "کل خرابی‌ها", "چند تا خرابی" (WITHOUT "تکراری").
- Logic: COUNT(DISTINCT Requests_Id)
- Specific Condition: (No RepeatRequest_Id filter).

----------------------------------------------------------------
2. Repeat Failure Count (تعداد خرابی‌های تکراری):
----------------------------------------------------------------
- Intent: User asks for "تعداد خرابی تکراری", "کل خرابی تکراری", "چند تا تکرار خرابی" (WITHOUT "نرخ" / "درصد").
- Logic: COUNT(DISTINCT Requests_Id)
- Specific Condition: RepeatRequest_Id IS NOT NULL

----------------------------------------------------------------
3. Repeat Failure Rate (نرخ تکرار خرابی):
----------------------------------------------------------------
- Intent: User explicitly asks for "نرخ تکرار خرابی", "درصد خرابی ت 6, 7, 8, 9, 10, 11)` filter as the numerator. NEVER divide by total requests without the State_Id filter.
- Do NOT write multiple independent SELECT statements or subqueries.
- Compute both numerator and denominator inside ONE single SELECT statement using conditional aggregation (CASE WHEN) so that all WHERE filters (Office, State_Id, Date) apply equally to both.
- Formula logic: (Count of distinct Requests_Id where RepeatRequest_Id is not null * 100.0) / NULLIF(Count of distinct Requests_Id, 0).
- Round the final percentage to 2 decimal places.
================================================================


================================================================
DELAY METRICS (تاخیر و نرخ تاخیر)
================================================================

Data source: ai_request_analysis
COMMON RULES FOR ALL DELAY METRICS:
- State filter: Always State_Id IN (1, 2, 5, 6, 7, 8, 9, 10, 11)
- IsCancel filter: Do NOT apply any IsCancel condition (do NOT check IsCancel = 0 or 1).
- Delay condition:  DelayReason_Id IS NOT NULL AND DelayReason_Id <> 0
- Office & Date: Strictly follow OFFICE (Area_Id = @MainAreaId OR ParentId = @MainAreaId) and CRITICAL DATE & TIMEFRAME RULES.
- Aggregation: Always use COUNT(DISTINCT Requests_Id).
----------------------------------------------------------------
1. Total Damage Count(تعداد کل خرابی‌ها):
----------------------------------------------------------------
- Intent: User asks for "تعداد خرابی", "کل خرابی‌ها", "چند تا خرابی" .
- Logic: COUNT(DISTINCT Requests_Id)
- Specific Condition: (No DelayReason_Id filter).
- Device Aggregation: ALWAYS use COUNT(DISTINCT DeviceID). NEVER write COUNT(DeviceID) without DISTINCT.
- Request Aggregation: ALWAYS use COUNT(DISTINCT Requests_Id).


----------------------------------------------------------------
2. Delay Count (تعداد تاخیر):
----------------------------------------------------------------
- Intent: User asks for "تعداد خرابی تکراری", "کل خرابی تکراری", "چند تا تکرار خرابی" (WITHOUT "نرخ" / "درصد").
- Logic: COUNT(DISTINCT Requests_Id)
- Specific Condition: DelayReason_Id IS NOT NULL 
- Specific Condition: DelayReasonID <> 0
----------------------------------------------------------------
3. Delay Rate (نرخ تاخیر):
----------------------------------------------------------------
- Intent: User asks for "نرخ تاخیر", "درصد تاخیر"
- Formula logic: (Delay Count * 100.0) / Total Damage Count.
- Round the final percentage to 2 decimal places.


================================================================
Failure Rate (نرخ خرابی)
================================================================



COMMON RULES FOR FAILURE RATE:


1. Cancellation Filter:
   - For ai_request_analysis:
     ALWAYS apply:
     IsCancel = 0

   - For ai_GetDeviceCount:
     Do NOT apply IsCancel.
     ai_GetDeviceCount does not contain the IsCancel column.
     Do NOT claim that cancelled requests are excluded from Device Count.

2. Office Filtering:
   - Inside ai_request_analysis:
     (Area_Id = @MainAreaId OR ParentId = @MainAreaId)

   - Inside ai_GetDeviceCount:
     (AreaId = @MainAreaId OR ParentId = @MainAreaId)
3. Strict Aggregation Rules:
   - Failure Count:
     ALWAYS use COUNT(DISTINCT Requests_Id)

   - Device Count:
     ALWAYS use COUNT(DISTINCT DeviceID)

   - NEVER use:
     COUNT(DeviceID)
     COUNT(Requests_Id)  
4. Time Filtering:
   - For ai_request_analysis:
     Filter using InsertedDate.

   - For ai_GetDeviceCount:
     Filter using Year and Month.

5. Failure Rate Formula:
   Failure Rate =
   Failure Count * 100.0 / Device Count

6. Division Safety:
   Use NULLIF(Device Count,  to prevent division-by-zero errors.

----------------------------------------------------------------
1. Failure Count (تعداد خرابی):
----------------------------------------------------------------
Data source: ai_request_analysis
- Intent: Number of service requests (excluding cancelled).
- Logic: COUNT(DISTINCT Requests_Id)

-IsCancel = 0
----------------------------------------------------------------
2. Device Count (تعداد دستگاه):
----------------------------------------------------------------
Data source:ai_GetDeviceCount
- Intent: Number of devices installed in offices.
- Logic: COUNT(DISTINCT DeviceID)
- Office & Date: Strictly follow OFFICE (AreaId = @MainAreaId OR ParentId = @MainAreaId) and CRITICAL DATE & TIMEFRAME RULES.
- Device Aggregation: ALWAYS use COUNT(DISTINCT DeviceID). NEVER write COUNT(DeviceID) without DISTINCT.
- Request Aggregation: ALWAYS use COUNT(DISTINCT Requests_Id).

----------------------------------------------------------------
3. Failure Rate (نرخ خرابی):
----------------------------------------------------------------

Failure Count divided by Device Count for the same office and time period.

Formula:Failure Rate =Failure Count*100 / Device Count


Important:
- Office filtering must be applied to both views.

- When filtering by time period:
  - ai_request_analysis → use InsertedDate
  - ai_GetDeviceCount → use Year and Month

Example SQL logic:

SELECT 
(
    SELECT COUNT(DISTINCT Requests_Id)
    FROM ai_request_analysis
    WHERE IsCancel = 0
    AND (Area_Id = @MainAreaId OR ParentId = @MainAreaId)
    AND InsertedDate BETWEEN 14050101 AND 14050131
) * 100
/
(
    SELECT COUNT(DISTINCT DeviceID)
    FROM ai_GetDeviceCount
    WHERE  (AreaId = @MainAreaId OR ParentId = @MainAreaId)
    AND Year = 1405
    AND Month = 1
)
================================================================
EXPERT SERVICE FREQUENCY METRICS: (فراوانی انجام سرویس  توسط کارشناس)
================================================================

- "فراوانی انجام سرویس توسط کارشناس" (Expert Service Frequency):
  - Definition: The number of service requests performed by each expert.
  - Formula: COUNT(DISTINCT Requests_Id)
  - Grouping: GROUP BY ExpertId (or ExpertTitle if available)
  - Filters:
    - Apply `State_Id IN (1,2,5,6,7,8,9,10,11)` (same standard request-state filter).
    - Do NOT apply the DelayReasonID filter to this metric.
    - Area filtering rules are the same as all other metrics: resolve by AreaTitle, then
      `Area_Id = @MainAreaId OR ParentId = @MainAreaId` (only inside ai_request_analysis).
  

"""
##############################################
CALENDAR = """
Persian months mapping:

فروردین = 01
اردیبهشت = 02
خرداد = 03
تیر = 04
مرداد = 05
شهریور = 06
مهر = 07
آبان = 08
آذر = 09
دی = 10
بهمن = 11
اسفند = 12

Dates are stored as Persian integers in format YYYYMMDD.
Example:
اردیبهشت 1405 = 14050201 to 14050231
"""
#####################################################
EXAMPLES = """

Example 1
Question: تعداد کل درخواست‌ها چقدر است؟
SQL:
SELECT COUNT(*) AS RequestCount
FROM ai_request_analysis
WHERE IsCancel = 0;


Example 2
Question: تعداد درخواست‌ها در هر دفتر
SQL:
SELECT AreaTitle, COUNT(*) AS RequestCount
FROM ai_request_analysis
WHERE IsCancel = 0
GROUP BY AreaTitle
ORDER BY RequestCount DESC;


Example 3
Question: بیشترین تاخیر مربوط به کدام دفتر است؟
SQL:
SELECT TOP 1 AreaTitle, MAX(DelayMinute) AS MaxDelay
FROM ai_request_analysis
WHERE IsCancel = 0
GROUP BY AreaTitle
ORDER BY MaxDelay DESC;


Example 4
Question: میانگین تاخیر هر برند
SQL:
SELECT Brand, AVG(DelayMinute) AS AvgDelay
FROM ai_request_analysis
WHERE IsCancel = 0
GROUP BY Brand
ORDER BY AvgDelay DESC;


Example 5
Question: بیشترین علت کنسلی چیست؟
SQL:
SELECT TOP 5 CancelReasonTitle, COUNT(*) AS CancelCount
FROM ai_request_analysis
WHERE IsCancel = 1
GROUP BY CancelReasonTitle
ORDER BY CancelCount DESC;


Example 6
Question: تعداد خرابی دفتر تهران در سال 1405
SQL:
SELECT COUNT(Distinct Requests_Id) AS FailureCount
FROM ai_request_analysis
WHERE IsCancel = 0
and (Area_Id = @MainAreaId OR ParentId = @MainAreaId)

AND InsertedDate BETWEEN 14050101 AND 14051229;


Example 7
Question: نرخ خرابی دفتر تهران در فروردین 1405
SQL:
SELECT
(
    SELECT COUNT(Distinct Requests_Id)
    FROM ai_request_analysis
    WHERE IsCancel = 0
    AND (Area_Id = @MainAreaId OR ParentId = @MainAreaId)
    AND InsertedDate BETWEEN 14050101 AND 14050131
) * 1.0
/
(
    SELECT COUNT(Distinct DeviceID)
    FROM ai_GetDeviceCount
    WHERE (Area_Id = @MainAreaId OR ParentId = @MainAreaId)
    AND Year = 1405
    AND Month = 1
) AS FailureRate;


Example 8
Question: تعداد دستگاه در دفتر تهران مرکز
SQL:
SELECT COUNT(Distinct DeviceID) AS DeviceCount
FROM ai_GetDeviceCount
WHERE Area_Id = @MainAreaId OR ParentId = @MainAreaId


Example 9
Question: نرخ خرابی تجهیز ATM و برند Wincore
SQL:
SELECT
(
    SELECT COUNT(Distinct Requests_Id)
    FROM ai_request_analysis
    WHERE IsCancel = 0
    AND Type LIKE N'%ATM%'
    AND Brand LIKE N'%Wincor%'
) * 1.0
/
(
    SELECT COUNT(Distinct DeviceID)
    FROM ai_GetDeviceCount
    WHERE Brand LIKE N'%Wincor%'
    AND DeviceType LIKE N'%ATM%'
) AS FailureRate;

Example 10: نرخ تاخیر دفتر اهواز در شهریور گذشته (ماه جاری در سال قبل)
SQL:
-- Example 10: نرخ تاخیر دفتر اهواز در شهریور گذشته (ماه جاری در سال قبل)
-- User Question: نرخ تاخیر دفتر اهواز در شهریور سال گذشته چقدر است؟

DECLARE @MainAreaId INT = (SELECT TOP 1 Area_Id FROM dbo.ai_request_analysis WHERE AreaTitle LIKE N'%اهواز%');
DECLARE @PrevYear INT, @CurrMonth INT, @CurrDay INT;
SELECT TOP 1 
    @PrevYear = CAST(CurrentPersianYear AS INT) - 1,
    @CurrMonth = CAST(CurrentPersianMonth AS INT),
    @CurrDay = CAST(CurrentPersianDay AS INT)
FROM dbo.ai_CurrentDateContext;

DECLARE @StartDate INT = (@PrevYear * 10000) + (@CurrMonth * 100) + 1;
DECLARE @EndDateMTD INT = (@PrevYear * 10000) + (@CurrMonth * 100) + @CurrDay;
DECLARE @LastDay INT = CASE WHEN @CurrMonth <= 6 THEN 31 WHEN @CurrMonth <= 11 THEN 30 ELSE 29 END;
DECLARE @EndDateFull INT = (@PrevYear * 10000) + (@CurrMonth * 100) + @LastDay;

SELECT
    -- ۱. بخش MTD (تا معادل روز جاری در سال قبل)
    COUNT(CASE WHEN InsertedDate <= @EndDateMTD THEN 1 END) AS TotalRequests_MTD,
    SUM(CASE WHEN InsertedDate <= @EndDateMTD AND DelayMinute > 0 THEN 1 ELSE 0 END) AS DelayedRequests_MTD,
    ROUND(CAST(SUM(CASE WHEN InsertedDate <= @EndDateMTD AND DelayMinute > 0 THEN 1 ELSE 0 END) AS FLOAT) * 100.0 / 
          NULLIF(COUNT(CASE WHEN InsertedDate <= @EndDateMTD THEN 1 END), 0), 2) AS DelayRate_MTD,

    -- ۲. بخش FullMonth (کل ماه در سال قبل)
    COUNT(*) AS TotalRequests_FullMonth,
    SUM(CASE WHEN DelayMinute > 0 THEN 1 ELSE 0 END) AS DelayedRequests_FullMonth,
    ROUND(CAST(SUM(CASE WHEN DelayMinute > 0 THEN 1 ELSE 0 END) AS FLOAT) * 100.0 / 
          NULLIF(COUNT(*), 0), 2) AS DelayRate_FullMonth

FROM dbo.ai_request_analysis
WHERE (Area_Id = @MainAreaId OR ParentId = @MainAreaId)
  AND State_Id IN (1,2,5,6,7,8,9,10,11)
  AND InsertedDate BETWEEN @StartDate AND @EndDateFull;

  
  
Example 11: نرخ تکرار خرابی در سال گذشته در ماه جاری که شامل دو پاسخ هست یکی تا پایان ماه جاری یکی تار روز جاری در سال گذشته
User Question: تعداد خرابی تکراری و تعداد کل خرابی و نرخ خرابی تکراری را در شهریور سال گذشته در دفتر شمال تهران بدهید
SQL:
DECLARE @MainAreaId INT = (SELECT TOP 1 Area_Id FROM ai_request_analysis WHERE AreaTitle LIKE N'%شمال تهران%');
DECLARE @PrevYear INT, @CurrMonth INT, @CurrDay INT;
SELECT TOP 1 
    @PrevYear = PreviousPersianYear, 
    @CurrMonth = CAST(CurrentPersianMonth AS INT), 
    @CurrDay = CAST(CurrentPersianDay AS INT) 
FROM dbo.ai_CurrentDateContext;

DECLARE @StartDate INT = (@PrevYear * 10000) + (@CurrMonth * 100) + 1;
DECLARE @EndDateMTD INT = (@PrevYear * 10000) + (@CurrMonth * 100) + @CurrDay;
DECLARE @LastDay INT = CASE WHEN @CurrMonth <= 6 THEN 31 WHEN @CurrMonth <= 11 THEN 30 ELSE 29 END;
DECLARE @EndDateFull INT = (@PrevYear * 10000) + (@CurrMonth * 100) + @LastDay;

SELECT 
    COUNT(DISTINCT CASE WHEN InsertedDate <= @EndDateMTD THEN Requests_Id END) AS TotalFailureCount_MTD,
    COUNT(DISTINCT CASE WHEN InsertedDate <= @EndDateMTD AND RepeatRequest_Id IS NOT NULL THEN Requests_Id END) AS RepeatFailureCount_MTD,
    CASE 
        WHEN COUNT(DISTINCT CASE WHEN InsertedDate <= @EndDateMTD THEN Requests_Id END) = 0 THEN 0
        ELSE ROUND(CAST(COUNT(DISTINCT CASE WHEN InsertedDate <= @EndDateMTD AND RepeatRequest_Id IS NOT NULL THEN Requests_Id END) AS FLOAT) * 100.0 / COUNT(DISTINCT CASE WHEN InsertedDate <= @EndDateMTD THEN Requests_Id END), 2)
    END AS RepeatFailureRatePercentage_MTD,

    COUNT(DISTINCT Requests_Id) AS TotalFailureCount_FullMonth,
    COUNT(DISTINCT CASE WHEN RepeatRequest_Id IS NOT NULL THEN Requests_Id END) AS RepeatFailureCount_FullMonth,
    CASE 
        WHEN COUNT(DISTINCT Requests_Id) = 0 THEN 0
        ELSE ROUND(CAST(COUNT(DISTINCT CASE WHEN RepeatRequest_Id IS NOT NULL THEN Requests_Id END) AS FLOAT) * 100.0 / COUNT(DISTINCT Requests_Id), 2)
    END AS RepeatFailureRatePercentage_FullMonth
FROM ai_request_analysis
WHERE (Area_Id = @MainAreaId OR ParentId = @MainAreaId)
  AND InsertedDate BETWEEN @StartDate AND @EndDateFull
  AND State_Id IN (1, 2, 5, 6, 7, 8, 9, 10, 11);



#----------------------------------
### Example 12
User: فراوانی انجام سرویس توسط هر کارشناس در مرداد ۱۴۰۴ در دفتر شمال تهران
SQL:
DECLARE @MainAreaId INT = (SELECT Area_Id FROM ai_request_analysis WHERE AreaTitle = N'دفتر شمال تهران');
SELECT
    YEAR(a.InsertedDate)  AS [Year],
    MONTH(a.InsertedDate) AS [Month],
    a.FullName,
    COUNT(DISTINCT a.Requests_Id) AS ServiceCount
FROM ai_request_analysis a
WHERE a.State_Id IN (1, 2, 5, 6, 7, 8, 9, 10, 11)
  AND (a.Area_Id = @MainAreaId OR a.ParentId = @MainAreaId)
  AND a.InsertedDate >= '14050501' AND a.InsertedDate <= '14050531'
GROUP BY YEAR(a.InsertedDate), MONTH(a.InsertedDate), a.FullName
ORDER BY ServiceCount DESC;



"""
