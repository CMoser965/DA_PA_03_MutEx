FROM python:3.11-alpine AS base

ARG NODE_ID
ARG PORT

EXPOSE ${PORT}
ENV ID=${NODE_ID}

WORKDIR /app
COPY . /app

CMD python3 /app/src/main.py ${ID}