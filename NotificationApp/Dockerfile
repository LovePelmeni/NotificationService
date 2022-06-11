FROM python:3.8.13-buster
WORKDIR /app/

ENV PYTHONUNBUFFERED=1
RUN pip install --upgrade pip
RUN pip install psycopg2-binary --no-input --no-cache-dir
RUN pip install gunicorn

COPY ./project/requirements.txt ./requirements.txt
RUN pip install -r ./requirements.txt
COPY . .

RUN chmod +x entrypoint.sh
ENTRYPOINT ["sh", "./entrypoint.sh"]


