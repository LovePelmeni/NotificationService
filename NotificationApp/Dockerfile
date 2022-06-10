FROM python:3.18.13-buster
WORKDIR /app/

ENV PYTHONUNBUFFERED=1
RUN pip install --upgrade pip
RUN pip install psycopg2-binary --no-input --no-cache-dir
RUN pip install gunicorn

COPY ./requirements.txt ./requirements.txt
RUN pip install -r ./requirements.txt

ENTRYPOINT ["sh", "./entrypoint.sh"]


