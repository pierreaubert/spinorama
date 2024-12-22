# FROM ubuntu/python:3.12-24.04_stable as base
FROM ubuntu:24.04_stable as base


LABEL org.opencontainers.image.authors="pierre@spinorama.org"
LABEL version="0.2"

WORKDIR /work

COPY src .
COPY scripts .
COPY tests .
COPY datas .

RUN /usr/bin/apt install -y dash libc-bin
RUN /usr/bin/localedef -f UTF-8 -i en_US en_US.UTF-8

RUN /usr/bin/python3.12 -m venv venv
RUN . venv/bin/activate
RUN pip3 install -U -r ./requirements.txt
RUN pip3 install -U -r ./requirements-test.txt
RUN pip3 install -U -r ./requirements-dev.txt
RUN pip3 install -U -r ./requirements-api.txt

RUN npm install .

ENV PYTHONPATH=/usr/src/spinorama/src:/usr/src/spinorama/src/website

RUN cd /work/src/spinorama && python setup.py build_ext --inplace && ln -s c_compute_scores.cpython-*.so c_compute_scores.so
CMD cd /work/spinorama && pytest tests
CMD cd /work/spinorama && vitest
CMD cd /work/spinorama && ./update_website.sh

EXPOSE 80
