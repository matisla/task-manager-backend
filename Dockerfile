FROM python:3.14

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code

COPY ./requirements.txt ./requirements.txt

RUN python -m pip install --root-user-action ignore --upgrade pip
RUN pip install --root-user-action ignore --no-cache-dir --upgrade -r requirements.txt

COPY ./app ./

EXPOSE 8000

CMD ["uvicorn", "app.asgi:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
