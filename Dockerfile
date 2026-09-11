FROM mcr.microsoft.com/playwright/python:v1.45.0-jammy

WORKDIR /app

# Установка зависимостей Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода проекта
COPY . .

# Открываем стандартный HTTP-порт для веб-сервера
EXPOSE 80

# Запуск Streamlit на 80 порту
CMD ["streamlit", "run", "app.py", "--server.port=80", "--server.address=0.0.0.0", "--server.headless=true"]
