FROM python:3.11-alpine AS base

ARG PORT_ARG=4000

ENV PORT = ${PORT_ARG}

WORKDIR /app
COPY . /app

CMD python3 /app/src/main.py
