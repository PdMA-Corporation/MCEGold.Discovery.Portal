# BuildKit required. Use only the context produced by prepare_context.py.
FROM mcegold-discovery:1.0.0

USER root

# Inputs are bind-mounted, and installation tooling lives only on tmpfs.
# No dependency resolution, index access, or global build-tool upgrades.
RUN --network=none \
    --mount=type=bind,source=.,target=/overlay,readonly \
    --mount=type=tmpfs,target=/tmp \
    cd /overlay && sha256sum -c SHA256SUMS \
    && python -m pip --isolated install --disable-pip-version-check \
        --no-cache-dir --no-index --no-deps --no-compile \
        --target /tmp/overlay-tools /overlay/setuptools-83.0.0-py3-none-any.whl \
    && PYTHONPATH=/tmp/overlay-tools SOURCE_DATE_EPOCH=1791331200 \
        python -m pip --isolated install --disable-pip-version-check \
        --no-cache-dir --no-index --no-deps --no-build-isolation \
        --no-compile --force-reinstall \
        /overlay/MCEGold.Discovery.PublicationCollector-v1.0.1.tar.gz \
    && rm -rf /app/portal/app

# Replacing the directory also removes modules deleted since v1.0.0.
# Includes the application's templates and static assets.
COPY --chown=mcegold:mcegold app/ /app/portal/app/

# The tested distribution added this template in a final follow-up layer.
# Include it here before verification; /config is seeded only at runtime.
COPY --chown=mcegold:mcegold collector.local.json /app/templates/collector.local.json

USER mcegold

# Import and cross-application SQLite checks use /tmp, never /data or /config.
RUN --network=none \
    --mount=type=bind,source=verify_image.py,target=/tmp/verify_image.py,readonly \
    cd /app/portal && PYTHONPATH=/app/portal python /tmp/verify_image.py

# Entrypoint, CMD, ports, workdir, environment, volumes and healthcheck inherited.
