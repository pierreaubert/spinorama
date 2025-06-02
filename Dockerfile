FROM spin-base:latest AS app

WORKDIR /work

COPY scripts .
COPY tests .
COPY datas .
COPY *.json .
COPY *.py .
COPY *.js .
COPY *.mjs .
COPY *.txt .

RUN python3.12 -m venv venv && \
    . venv/bin/activate && \
    pip3 install -U -r ./requirements.txt && \
    pip3 install -U -r ./requirements-test.txt && \
    pip3 install -U -r ./requirements-dev.txt

RUN npm install

ENV PYTHONPATH=/usr/src/spinorama/src:/usr/src/spinorama/src/website

RUN cd /work/src/spinorama && \
    python3.12 setup.py build_ext --inplace && \
    ln -s c_compute_scores.cpython-*.so c_compute_scores.so

CMD ["bash", "-c", "cd /work/spinorama && pytest tests && vitest"]

EXPOSE 80
