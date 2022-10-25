FROM python:3.7-slim

RUN apt-get clean \
    && apt-get -y update

RUN apt-get -y install \
    postgresql \
    nginx \
    python3-dev \
    build-essential

RUN apt-get install \
    --reinstall libpq-dev

WORKDIR /app

COPY API.py /app/API.py
COPY requirements-api.txt /app/requirements.txt
RUN pip install -r requirements.txt --src /usr/local/src

COPY . .

EXPOSE 8080
CMD [ "python3", "API.py" ]
