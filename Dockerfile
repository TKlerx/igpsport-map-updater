# Runtime-fetch Osmosis 0.49.2 and Mapsforge writer 0.27.0 via existing script.sh.
FROM ghcr.io/astral-sh/uv:0.11.2 AS uv

FROM debian:trixie-slim

ARG UID=1000
ARG GID=1000

ENV PATH="/work/.venv/bin:/usr/local/bin:${PATH}" \
    UV_LINK_MODE=copy \
    UV_PYTHON_INSTALL_DIR=/opt/uv/python \
    PYTHON=python3

WORKDIR /work

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        bc \
        ca-certificates \
        curl \
        default-jre-headless \
        osmium-tool \
        python3 \
        python3-venv \
        unzip \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /uvx /usr/local/bin/

COPY . /work

RUN sed -i 's/\r$//' /work/run.sh /work/script.sh \
    && chmod +x /work/run.sh /work/script.sh \
    && uv sync --locked \
    && mkdir -p /work/download /work/tmp /work/output /work/packages /work/input \
    && { \
        echo "Base: debian:trixie-slim"; \
        java -version 2>&1; \
        uv --version; \
        osmium --version; \
        dpkg-query -W -f='osmium-tool ${Version}\n' osmium-tool; \
      } > /work/.tool-versions \
    && groupadd --gid "${GID}" app \
    && useradd --uid "${UID}" --gid "${GID}" --home-dir /work --shell /bin/bash app \
    && chown -R "${UID}:${GID}" /work /opt/uv

USER app

CMD ["bash"]
