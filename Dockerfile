# FROM - impot
# ENV - environment variables
# RUN - execute the command in shell
# WORKDIR - change directory in file system
# COPY - copy from host-machine to the container
# CMD - command to execute


FROM python:3.13-slim as base

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

# ====================================================
# MULTI-STAGE BUILDS FOR ENVIRONMENTS
# ====================================================

FROM base AS dev

RUN pipenv install sync --dev --system

EXPOSE 8000/tcp
ENTRYPOINT [ "python" ]
CMD [ "manage.py", "runserver", "0.0.0.0:8000" ]


FROM base AS prod

RUN pipenv install --deploy --system

EXPOSE 8000/tcp
ENTRYPOINT [ "python" ]
CMD [ "-m", "gunicorn", "config.wsgi:application" ]

# ====================================================
# MULTI-STAGE BUILDS FOR PROVIDERS
# ====================================================

FROM base AS silpo

RUN pipenv install sync --dev --system

EXPOSE 8000/tcp
ENTRYPOINT [ "python" ]
CMD [ "-m", "uvicorn", "tests.providers.silpo:app", "--host", "0.0.0.0" ]


FROM base AS kfc

RUN pipenv install sync --dev --system

EXPOSE 8000/tcp
ENTRYPOINT [ "python" ]
CMD [ "-m", "uvicorn", "tests.providers.kfc:app", "--host", "0.0.0.0" ]


FROM base AS uklon

RUN pipenv install sync --dev --system

EXPOSE 8000/tcp
ENTRYPOINT [ "python" ]
CMD [ "-m", "uvicorn", "tests.providers.uklon:app", "--host", "0.0.0.0" ]