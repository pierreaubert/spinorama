FROM ubuntu:22.04 as base

LABEL org.opencontainers.image.authors="pierre@spinorama.org"
LABEL version="0.1"

RUN rm -f /etc/apt/apt.conf.d/docker-clean; echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt update && \
    apt-get --no-install-recommends install -y ca-certificates curl gnupg python3 python3-pip imagemagick keychain npm wget libc-bin locales python3.10-venv && \
    locale-gen en_US.UTF-8

WORKDIR /usr/src/spinorama

COPY . .

RUN [ -x /usr/bin/apt ] && /usr/bin/apt install -y python3 python3-pip imagemagick keychain npm wget python3.10-venv
RUN [ -x /usr/bin/localedef ] && /usr/bin/localedef -f UTF-8 -i en_US en_US.UTF-8
RUN /usr/bin/python3.10 -m venv venv
RUN . venv/bin/activate
RUN pip3 install -U -r ./requirements.txt && \
    pip3 install -U -r ./requirements-test.txt && \
    pip3 install -U -r ./requirements-dev.txt && \
    pip3 install -U -r ./requirements-api.txt

RUN npm install .

# FROM ubuntu:22.04 AS final

ENV PYTHONPATH=/usr/src/spinorama/src:/usr/src/spinorama/src/website

RUN cd /usr/src/spinorama/src/spinorama && python setup.py build_ext --inplace && ln -s c_compute_scores.cpython-*.so c_compute_scores.so
CMD cd /usr/src/spinorama && pytest tests
CMD cd /usr/src/spinorama && ./update_website.sh

EXPOSE 443
