from python:3.6

COPY requirements.txt /opt/
RUN pip install -r /opt/requirements.txt

COPY covid /opt/covid

WORKDIR /opt/covid
