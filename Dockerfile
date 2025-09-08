FROM spin-base:latest AS app

WORKDIR /work

ENV VIRTUAL_ENV=/work/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY src .
COPY scripts .
COPY tests .
COPY *.json .
COPY *.py .
COPY *.js .
COPY *.mjs .
COPY *.txt .

RUN /usr/bin/python3.12 -m venv .venv && \
    pip install -U pip && \
    pip install -U -r requirements.txt && \
    pip install -U -r requirements-test.txt && \
    pip install -U -r requirements-dev.txt && \
    pip install -U -r requirements-api.txt && \
    pip install -U -r requirements-meta.txt && \
    pip install -U -r requirements-scrape.txt

RUN npm install && chmod +x update_3rdparties.sh && sh update_3rdparties.sh

ENV PYTHONPATH=/work:/work/website

RUN cd /work/spinorama/compute_scores_cython && \
    python setup.py build_ext --inplace

RUN cd /work/spinorama/compute_scores_rust && \
    maturin develop --release

RUN mkdir -p build dist && \
    flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --exclude .venv || true

CMD ["bash", "-lc", "pytest -q tests && npx vitest run"]

EXPOSE 80
