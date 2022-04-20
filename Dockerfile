FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8

WORKDIR /app
RUN python -m venv .venv
COPY requirements.txt .

ENV PATH="/app/.venv/bin:$PATH"
RUN pip install -r requirements.txt

EXPOSE 8000
COPY ./app/src /app/src

WORKDIR /app/src

CMD ["uvicorn", "testStarlette:app", "--app-dir", "/app/src", "--reload", "--host", "0.0.0.0","--port","8000"]
