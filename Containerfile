FROM ghcr.io/blindfoldedsurgery/poetry:2.0.1-pipx-3.12-bookworm

COPY [ "poetry.lock", "pyproject.toml", "./" ]

RUN poetry install --no-interaction --ansi --only=main --no-root

COPY  src/cure_freedom_bot ./src/cure_freedom_bot

RUN poetry install --no-interaction --ansi --only-root

ARG APP_VERSION
ENV APP_VERSION=$APP_VERSION

ENTRYPOINT [ "tini", "--", "poetry", "run", "python", "-m", "cure_freedom_bot.main" ]
