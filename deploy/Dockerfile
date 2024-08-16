FROM python:3.11.4-slim-bullseye as prod

RUN apt-get update && \
    apt-get install -y python3-pip python3-dev python-is-python3 && \
    rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y \
  gcc \
  git \
  && rm -rf /var/lib/apt/lists/*


RUN pip install poetry==1.4.2

# Configuring poetry
RUN poetry config virtualenvs.create false

# # Copying requirements of a project
COPY pyproject.toml poetry.lock /var/www/mlab/server/
WORKDIR /var/www/mlab/server

# Copy from local /var to container /var
# ADD ../filez/models /var/lib/docker/volumes/filez/
# COPY ../filez/models /var/lib/docker/volumes/filez/

# Installing requirements
RUN poetry install --only main
# Removing gcc
RUN apt-get purge -y \
  gcc \
  && rm -rf /var/lib/apt/lists/*

# Copying actuall application
COPY . /var/www/mlab/server

# copy ssh key from host to container
RUN poetry install --only main

CMD ["/usr/local/bin/python", "-m", "server"]

FROM prod as dev

RUN poetry install
