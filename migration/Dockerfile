FROM python:3.11-slim

WORKDIR /app

# نصب ابزارهای پایه
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    gnupg \
    apt-transport-https \
    unixodbc \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# اضافه کردن کلید مایکروسافت به روش جدید (سازگار با دبیان 11 و 12)
RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg

# اضافه کردن مخزن مایکروسافت برای دبیان 12 (Bookworm) 
# اگر داکر شما قدیمی است و از دبیان 11 استفاده می‌کند، عدد 12 را به 11 تغییر دهید
RUN curl https://packages.microsoft.com/config/debian/12/prod.list > /etc/apt/sources.list.d/mssql-release.list

# نصب درایور با ارجاع به کلید جدید
RUN apt-get update && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql17 \
    && rm -rf /var/lib/apt/lists/*

# کپی و نصب نیازمندی‌های پایتون
COPY migration/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY . /app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
