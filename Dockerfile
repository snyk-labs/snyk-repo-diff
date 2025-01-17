# This is a multistage container builder for poetry projects

FROM python:3.14.0a1-slim AS requirements

ENV PYTHONDONTWRITEBYTECODE 1

# step one is to create a container with poetry on it
RUN python -m pip install --quiet -U pip poetry

WORKDIR /src

COPY pyproject.toml pyproject.toml
COPY poetry.lock poetry.lock

# now that we have poetry, we export the requirements file
RUN poetry export --quiet --no-interaction -f requirements.txt --without-hashes -o /src/requirements.txt

# now we create our final container, runtime
FROM python:3.14.0a1-slim AS runtime

WORKDIR /app

# copy stuff from this repo into the /app directory of the container
COPY *.py .

# now we use multistage containers to then copy the requirements from the other container
COPY --from=requirements /src/requirements.txt .

# now we're *just* deploying the needed packages for whatever was in the poetry setup
RUN python -m pip install --quiet -U pip
RUN pip install --quiet -r requirements.txt
RUN mkdir /app/output

ENTRYPOINT ["/usr/local/bin/python","/app/repo_diff.py"]