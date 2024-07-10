# server

This project was generated using fastapi_template.

## Poetry

This project uses poetry. It's a modern dependency management
tool.

To run the project use this set of commands:

```bash
poetry install
poetry run python -m server
```

This will start the server on the configured host.

You can find swagger documentation at `/api/docs`.

You can read more about poetry here: https://python-poetry.org/

## Docker

You can start the project with docker using this command:

```bash
docker-compose -f deploy/docker-compose.yml --project-directory . up --build
```

If you want to develop in docker with autoreload add `-f deploy/docker-compose.dev.yml` to your docker command.
Like this:

```bash
docker-compose -f deploy/docker-compose.yml -f deploy/docker-compose.dev.yml --project-directory . up --build
```

This command exposes the web application on port 8000, mounts current directory and enables autoreload.

But you have to rebuild image every time you modify `poetry.lock` or `pyproject.toml` with this command:

```bash
docker-compose -f deploy/docker-compose.yml --project-directory . build
```

## Project structure

```bash
$ tree "server"
server
├── conftest.py  # Fixtures for all tests.
├── db  # module contains db configurations
│   ├── dao  # Data Access Objects. Contains different classes to interact with database.
│   └── models  # Package contains different models for ORMs.
├── __main__.py  # Startup script. Starts uvicorn.
├── services  # Package for different external services such as rabbit or redis etc.
├── settings.py  # Main configuration settings for project.
├── static  # Static content.
├── tests  # Tests for project.
└── web  # Package contains web server. Handlers, startup config.
    ├── api  # Package with all handlers.
    │   └── router.py  # Main router.
    ├── application.py  # FastAPI application configuration.
    └── lifetime.py  # Contains actions to perform on startup and shutdown.
```

## Configuration

This application can be configured with environment variables.

You can create `.env` file in the root directory and place all
environment variables here.

All environment variables should start with "SERVER_" prefix.

For example if you see in your "server/settings.py" a variable named like
`random_parameter`, you should provide the "SERVER_RANDOM_PARAMETER"
variable to configure the value. This behaviour can be changed by overriding `env_prefix` property
in `server.settings.Settings.Config`.

An example of .env file:
```bash
SERVER_RELOAD="True"
SERVER_PORT="8000"
SERVER_ENVIRONMENT="dev"
```

You can read more about BaseSettings class here: https://pydantic-docs.helpmanual.io/usage/settings/

## Pre-commit

To install pre-commit simply run inside the shell:
```bash
pre-commit install
```

pre-commit is very useful to check your code before publishing it.
It's configured using .pre-commit-config.yaml file.

By default it runs:
* black (formats your code);
* mypy (validates types);
* isort (sorts imports in all files);
* flake8 (spots possible bugs);


You can read more about pre-commit here: https://pre-commit.com/

## Migrations

If you want to migrate your database, you should run following commands:
```bash
# To run all migrations until the migration with revision_id.
alembic upgrade "<revision_id>"

# To perform all pending migrations.
alembic upgrade "head"
```

### Reverting migrations

If you want to revert migrations, you should run:
```bash
# revert all migrations up to: revision_id.
alembic downgrade <revision_id>

# Revert everything.
 alembic downgrade base
```

### Migration generation

To generate migrations you should run:
```bash
# For automatic change detection.
alembic revision --autogenerate

# For empty file generation.
alembic revision
```


## Running tests

If you want to run it in docker, simply run:

```bash
docker-compose -f deploy/docker-compose.yml -f deploy/docker-compose.dev.yml --project-directory . run --build --rm api pytest -vv .
docker-compose -f deploy/docker-compose.yml -f deploy/docker-compose.dev.yml --project-directory . down
```

For running tests on your local machine.
1. you need to start a database.

I prefer doing it with docker:
```
docker run -d -p "5432:5432" -e "POSTGRES_PASSWORD=mlab@123" -e "POSTGRES_USER=mlab" -e "POSTGRES_DB=mlab" -e "PGDATA=/var/lib/postgresql/data/pgdata" -v "/Users/disal/work/disal/mlab/mlab-db:/var/lib/postgresql/data" postgres:13.8-bullseye 
```

```
docker run -d -p "6379:6379" redis redis-server --save 60 1 --loglevel warning
```


2. Run the pytest.
```bash
pytest -vv .
```

## Server Deploy

```bash

poetry config virtualenvs.create false
docker-compose -f deploy/docker-compose.yml --project-directory . up --build -d
sudo cp -r ~/Projects/MLab/mlab-server/. . 
sudo cp -r ~/Projects/MLab/mlab-server/. . | yes

docker-compose -f deploy/docker-compose.yml --project-directory . down
docker-compose -f deploy/docker-compose.yml --project-directory . logs
cd /var/www/mlab/server/
git pull
cd ~/Projects/MLab/mlab-server/

sudo docker-compose -f deploy/docker-compose-db.yml --project-directory . up -d

docker-compose -f deploy/docker-compose.yml --project-directory . run --rm alembic merge heads 
docker-compose -f deploy/docker-compose.yml --project-directory . run --rm alembic merge heads --force
docker-compose -f deploy/docker-compose.yml --project-directory . run --rm alembic history

poetry source show

# ssh-keygen -t rsa -b 4096 -C "", if you don't have ssh key
# cat ~/.ssh/id_rsa.pub | pbcopy
# paste the key in the mlab ssh keys configuration
# eval $(ssh-agent)
# ssh-add
# git clone disal@appatechlabb.com:6000/path/to/project.git
