FROM spark-py:3.3.0

USER root

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

COPY Main.py /app/Main.py
COPY Model.py /app/Model.py
COPY requirements-model.txt /app/requirements.txt
RUN pip install -r requirements.txt --src /usr/local/src

COPY . .

CMD [ "python3", "Main.py" ]
