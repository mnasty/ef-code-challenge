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

COPY res/jars/ ${SPARK_HOME}/jars
COPY res/models /app/res/models
COPY Main.py /app/Main.py
COPY Model.py /app/Model.py
COPY version.txt /app/version.txt
COPY requirements-model.txt /app/requirements.txt
RUN pip install -r requirements.txt --src /usr/local/src

# TODO: remove this
#COPY . .

# TODO: remove this
#CMD [ "python3", "Main.py" ]
