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

SELECT COUNT(DeviceID)
FROM ai_GetDeviceCount

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

SELECT COUNT(DeviceID)
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
CRITICAL RULE: OFFICE & SATELLITES FILTERING (اقماری)
================================================================
- When the user asks for an office (e.g. "دفتر اهواز"), you MUST NEVER write:
  ❌ AreaTitle = N'دفتر اهواز'
  ❌ AreaTitle LIKE N'%اهواز%'
  (Because satellite offices like Abadan, Mahshahr, Dezful DO NOT have 'اهواز' in their name!)

- Instead, you MUST filter by Area_Id and ParentId using the office ID (Ahvaz ID = 67):
  ✅ WHERE (f.Area_Id = 67 OR f.ParentId = 67)
  OR
  ✅ WHERE f.Area_Id IN (SELECT 67 UNION SELECT DISTINCT Area_Id FROM dbo.ai_request_analysis WHERE ParentId = 67)

----------------------------------------------------------------
TEMPLATE: REPEATED FAILURES / CAUSES (علت تکرار خرابی)
----------------------------------------------------------------
When answering failure reasons for Ahvaz (ID = 67) in Tir 1405:

SELECT 
    f.AreaTitle,
    f.FailureReason,         -- or the exact column name for failure cause in your schema
    COUNT(*) AS RepeatCount
FROM dbo.ai_request_analysis AS f
WHERE (f.Area_Id = 67 OR f.ParentId = 67)
  AND f.PersianDate >= '1405/04/01' 
  AND f.PersianDate <= '1405/04/31'
GROUP BY 
    f.AreaTitle,
    f.FailureReason
ORDER BY 
    RepeatCount DESC;

================================================================
MANDATORY CONSTRAINTS:
1. Do NOT put `AreaTitle LIKE` or `AreaTitle =` anywhere in the query.
2. If the user asks for a table, include `f.AreaTitle` in SELECT and GROUP BY so satellite offices (آبادان، ماهشهر، دزفول) clearly appear in the table rows.
3. Ahvaz Area_Id is 67. All its satellite offices have `ParentId = 67`.
================================================================



Business Metrics Definitions

Failure Count (تعداد خرابی):
Number of service requests (excluding cancelled).

SQL logic:
COUNT(Requests_Id)

Data source:
ai_request_analysis

Filter:
IsCancel = 0


Device Count (تعداد دستگاه):
Number of devices installed in offices.

SQL logic:
COUNT(DeviceID)

Data source:
ai_GetDeviceCount


Failure Rate (نرخ خرابی):
Failure Count divided by Device Count for the same office and time period.

Formula:

Failure Rate =
Failure Count / Device Count

Failure Count source:
ai_request_analysis

Device Count source:
ai_GetDeviceCount

Important:
- Office filtering must be applied to both views.
- Use LIKE for AreaTitle.
- When filtering by time period:
  - ai_request_analysis → use InsertedDate
  - ai_GetDeviceCount → use Year and Month

Example SQL logic:

SELECT 
(
    SELECT COUNT(Requests_Id)
    FROM ai_request_analysis
    WHERE IsCancel = 0
    AND (Area_Id = @MainAreaId OR ParentId = @MainAreaId)
    AND InsertedDate BETWEEN 14050101 AND 14050131
) * 1.0
/
(
    SELECT COUNT(DeviceID)
    FROM ai_GetDeviceCount
    WHERE  (Area_Id = @MainAreaId OR ParentId = @MainAreaId)
    AND Year = 1405
    AND Month = 1
)


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
REPEAT FAILURE RATE
نرخ خرابی‌های تکراری
================================================================

Repeat Failure Rate (نرخ خرابی‌های تکراری):
The number of repeat failure requests divided by the total number of damage/failure requests for the same office and time period, expressed as a percentage.

Formula:

Repeat Failure Rate =
(Repeat Failure Count * 100) / Count all Damage

Repeat Failure Count source:
ai_request_analysis
Conditions:
- RepeatRequest_Id IS NOT NULL
- State_Id IN (1, 2, 5, 6, 7, 8, 9, 10, 11)

Count all Damage source:
ai_request_analysis
Conditions:
- State_Id IN (1, 2, 5, 6, 7, 8, 9, 10, 11)

Important:
- Both Repeat Failure Count and Count all Damage come from the same view: ai_request_analysis.
- State_Id IN (1, 2, 5, 6, 7, 8, 9, 10, 11) must be applied to both numerator and denominator.
- Office filtering (such as AreaTitle) and time period filtering (InsertedDate) must be applied identically to both numerator and denominator.
- Do NOT use AreaTitle for office filtering when Area_Id / ParentId is available.
- Use Area_Id and ParentId for office filtering.
- Multiply the numerator by 100.0 to prevent integer division in SQL Server.
- Use NULLIF(..., 0) for the denominator to prevent divide-by-zero errors.

Example SQL logic:

SELECT 
(
    SELECT COUNT(Requests_Id)
    FROM ai_request_analysis
    WHERE RepeatRequest_Id IS NOT NULL
      AND State_Id IN (1, 2, 5, 6, 7, 8, 9, 10, 11)
      AND (Area_Id = @MainAreaId OR ParentId = @MainAreaId)
      AND InsertedDate BETWEEN 14050101 AND 14050131
) * 100.0
/
NULLIF(
(
    SELECT COUNT(Requests_Id)
    FROM ai_request_analysis
    WHERE State_Id IN (1, 2, 5, 6, 7, 8, 9, 10, 11)
      AND (Area_Id = @MainAreaId OR ParentId = @MainAreaId)
      AND InsertedDate BETWEEN 14050101 AND 14050131
), 0) AS RepeatFailureRate


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
SELECT COUNT(Requests_Id) AS FailureCount
FROM ai_request_analysis
WHERE IsCancel = 0
AND AreaTitle LIKE N'%تهران%'
AND InsertedDate BETWEEN 14050101 AND 14051229;


Example 7
Question: نرخ خرابی دفتر تهران در فروردین 1405
SQL:
SELECT
(
    SELECT COUNT(Requests_Id)
    FROM ai_request_analysis
    WHERE IsCancel = 0
    AND AreaTitle LIKE N'%تهران%'
    AND InsertedDate BETWEEN 14050101 AND 14050131
) * 1.0
/
(
    SELECT COUNT(DeviceID)
    FROM ai_GetDeviceCount
    WHERE AreaTitle LIKE N'%تهران%'
    AND Year = 1405
    AND Month = 1
) AS FailureRate;


Example 8
Question: تعداد دستگاه در دفتر تهران مرکز
SQL:
SELECT COUNT(DeviceID) AS DeviceCount
FROM ai_GetDeviceCount
WHERE AreaTitle LIKE N'%تهران مرکز%';


Example 9
Question: نرخ خرابی تجهیز ATM و برند Wincore
SQL:
SELECT
(
    SELECT COUNT(Requests_Id)
    FROM ai_request_analysis
    WHERE IsCancel = 0
    AND Type LIKE N'%ATM%'
    AND Brand LIKE N'%Wincor%'
) * 1.0
/
(
    SELECT COUNT(DeviceID)
    FROM ai_GetDeviceCount
    WHERE Brand LIKE N'%Wincor%'
    AND DeviceType LIKE N'%ATM%'
) AS FailureRate;
"""
