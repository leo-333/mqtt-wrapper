FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8

EXPOSE 8080
COPY ./app /app

CMD ["uvicorn", "testStarlette:app", "--reload", "--host", "0.0.0.0","--port","2376"]
