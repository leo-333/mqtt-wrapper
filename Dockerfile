FROM python:3.9

WORKDIR /app
RUN python -m venv .venv
COPY requirements.txt .

ENV PATH="/app/.venv/bin:$PATH"
RUN pip install -r requirements.txt

EXPOSE 8000
COPY ./app /app/src

WORKDIR /app/src

CMD ["python", "main.py"]
