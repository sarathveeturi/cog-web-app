FROM python:3.9.13

WORKDIR /server-app

COPY requirements.txt /server-app
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY . /server-app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]



