# FROM - impot
# ENV - environment variables
# RUN - execute the command in shell
# WORKDIR - change directory in file system
# COPY - copy from host-machine to the container
# CMD - command to execute


FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Update System Dependencies
RUN apt-get update -y \
    # dependencies for building Python packages && clean apt packages
    && apt-get install -y build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set Working Dir
WORKDIR /app

# Update Project Dependencies
RUN pip install --upgrade pip setuptools pipenv

# Install deps
COPY Pipfile Pipfile.lock ./

# Copy project files
COPY . .
RUN ls -l /app

# ====================================================
# MULTI-STAGE BUILDS FOR ENVIRONMENTS
# ====================================================

FROM base AS dev

ENV C_FORCE_ROOT="true"
ENV DJANGO_DEBUG=1

RUN pipenv sync --dev --system

EXPOSE 8000/tcp
ENTRYPOINT [ "python" ]
CMD [ "manage.py", "runserver", "0.0.0.0:8000" ]


FROM base AS prod

ENV DJANGO_DEBUG=
ENV GUNICORN_CMD_ARGS="--bind 0.0.0.0:8000 --reload"

RUN pipenv install --deploy --system

EXPOSE 8000/tcp
ENTRYPOINT [ "python" ]
CMD [ "-m", "gunicorn", "config.wsgi:application" ]
