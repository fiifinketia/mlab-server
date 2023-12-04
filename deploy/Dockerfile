FROM python:3.11.4-slim-bullseye as prod
RUN apt-get update && apt-get install -y \
  gcc \
  && rm -rf /var/lib/apt/lists/*


RUN pip install poetry==1.4.2

# Configuring poetry
RUN poetry config virtualenvs.create false

# Copying requirements of a project
COPY pyproject.toml poetry.lock /app/src/
WORKDIR /app/src

# Copy from local /var to container /var
# ADD ../filez/models /var/lib/docker/volumes/filez/
# COPY ../filez/models /var/lib/docker/volumes/filez/

# Installing requirements
RUN poetry install --only main
# Removing gcc
RUN apt-get purge -y \
  gcc \
  && rm -rf /var/lib/apt/lists/*

# RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y to install cv2 dependencies
RUN apt-get update && apt-get install lib1 python3-opencv -y

# Copying actuall application
COPY . /app/src/
RUN poetry install --only main

CMD ["/usr/local/bin/python", "-m", "server"]

FROM prod as dev

RUN poetry install
