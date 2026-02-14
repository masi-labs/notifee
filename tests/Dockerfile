FROM python:3.14-alpine

ENV PYTHONPATH=/code/src
ENV PYTHONOPTIMIZE=''
ENV PYTHONDONTWRITEBYTECODE=1

COPY requirements/* /code/requirements/

RUN pip install -r /code/requirements/dev.txt

WORKDIR /code
