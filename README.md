# repo_diff.py

Helping answer which repositories aren't monitored by Snyk?

This works by retrieving a list of all projects in a given Snyk Group (so all projects in all orgs belonging to the same Snyk Group) and associating them with a list of repositories found in a given GitHub Organization. If one wants to check against multiple GitHub Organizations, currently run this script multiple times, providing a different GitHub Org each time.

Once the list is generating, the script can output a CSV or JSON file of the repositories that do not appear to have any projects in Snyk. There is an optional --with-projects flag that output all repositories and the count (in CSV) of projects or a link to every project (in JSON).

The data also includes the last update of the repository itself. Many organizations have old or stale repositories, so Snyk not having any projects for a repository last updated in 2016 might not be as important as one updated yesterday.


## Requirements
In order to run this script one needs a python environment with the Snyk, Github, and Typer libraries. Use the provided Dockerfile to build and run a container with this script setup in it. Refer to the [Docker](#user-content-running-with-docker) section for more information.

### Snyk Requirements
- Snyk Access Token: Either generate an service account token or [retrieve your own](https://docs.snyk.io/snyk-api-info/authentication-for-api)
- Snyk Group ID: Available under the Settings view of your Group page at [app.snyk.io](https://app.snyk.io/)

### GitHub Requirements
- GitHub Token: A token with access to list / view all repositories inside the organization you are checking. See GitHub's documentation on generating a [personal access token](https://docs.github.com/en/github/authenticating-to-github/keeping-your-account-and-data-secure/creating-a-personal-access-token).
- Name of the GitHub organization you are checking for repositories

### Environment Variables

While you can pass the GitHub and Snyk tokens as commandline arguments to the script, it is best to use them as environment variables so they aren't stored in your workstation's command history. Use example_secrets.sh if you need a simple way to copy/paste your tokens into a file and then load them into your environment for use.

Refer to --help for more environment variables:
```shell
> repo_diff.py --help
Usage: repo_diff.py [OPTIONS] COMMAND [ARGS]...

Options:
  --snyk-token TEXT    Snyk Token with access to the Group whose projects you
                       to want to audit against a Github Organization  [env
                       var: SNYK_TOKEN; required]
  --snyk-group TEXT    Only projects associated with the Snyk Group are
                       checked for  [env var: SNYK_GROUP; required]
  --github-token TEXT  GitHub Token with read access to the GitHub Org you
                       wish to audit  [env var: GITHUB_TOKEN; required]
  --github-org TEXT    Name of the GitHub Org whose repositories you want to
                       check  [env var: GITHUB_ORG; required]
  --with-projects      Include repositories that have projects
  --out-file FILENAME  Full path to where the output should be saved  [env
                       var: REPO_DIFF_OUTPUT; required]
  --format [csv|json]  [default: csv]
  --origin TEXT        Specify which Snyk integrations to check for projects
                       [default: github, github-enterprise]
  --help               Show this message and exit.
```

## Running with Docker

1) Build the container with docker, a command like this should suffice:<p>
`docker build --pull --no-cache --force-rm -f Dockerfile -t repo_diff .`
    ```shell
    ❯ docker build --pull --no-cache --force-rm -f Dockerfile -t repo_diff .
    [+] Building 24.0s (17/17) FINISHED                                                                                  
    => [internal] load build definition from Dockerfile
    => => transferring dockerfile: 37B
    => [internal] load .dockerignore
    => => transferring context: 2B
    => [internal] load metadata for docker.io/library/python:3.9-slim
    => CACHED [requirements 1/6] FROM docker.io/library/python:3.9-slim@sha256:cd1045dbabff11dab74379e25f7974aa76
    => [internal] load build context
    => => transferring context: 100B
    => CACHED [runtime 2/7] WORKDIR /app
    => [requirements 2/6] RUN python -m pip install -U pip poetry
    => [runtime 3/7] COPY *.py .
    => [requirements 3/6] WORKDIR /src
    => [requirements 4/6] COPY pyproject.toml pyproject.toml
    => [requirements 5/6] COPY poetry.lock poetry.lock
    => [requirements 6/6] RUN poetry export -f requirements.txt --without-hashes -o /src/requirements.txt 
    => [runtime 4/7] COPY --from=requirements /src/requirements.txt . 
    => [runtime 5/7] RUN python -m pip install -U pip 
    => [runtime 6/7] RUN pip install -r requirements.txt 
    => [runtime 7/7] RUN mkdir /output 
    => exporting to image 
    => => exporting layers 
    => => writing image sha256:09687a554bb04397641490538185324be3eab462e31c2e80a59312a0b143a483 
    => => naming to docker.io/library/repo_diff 
    ```

2) Run the container with the `docker run` command, ensuring to:
    - Pass a local volume (`-v "${PWD}/output":/output`) for the csv output to be saved to
    - Pass the SNYK_TOKEN and GITHUB_TOKEN environment variables (`-e SNYK_TOKEN -e GITHUB_TOKEN`)
    - Delete the container image after use (`--rm`)
    - Specify the `--snyk-group`, `--github-org`, and `--out-file` options for the script
    ```shell
    ❯ docker run --rm -v "${PWD}/output":/output -e SNYK_TOKEN -e GITHUB_TOKEN -it repo-diff \
    --out-file /output/output.csv \
    --snyk-group 36863d40-ba29-491f-af63-7a1a7d79e411 \
    --github-org snyk-playground

    Searching Snyk for Projects from snyk-playground repositories
    Searching 7 Snyk Org(s) with ('github', 'github-enterprise') Projects  [####################################]  100%          
    Checking for Projects from the 27 repos in snyk-playground  [####################################]  100%          
    Formatting and writing results to /output/output.csv
    ```

3) An example output.csv should look something like this:
    ```
    Repository Name,Last Updated,Is Fork,Snyk Project Count
    snyk-playground/snyk-container-scan-docker,2018-12-06 22:59:40,False,0
    snyk-playground/config-repo,2021-08-06 09:51:10,False,0
    snyk-playground/webhook-test-repository,2021-06-30 13:12:17,False,0
    snyk-playground/pygithub-import-parser,2021-08-25 12:27:04,False,0
    snyk-playground/docs,2021-07-24 04:55:03,False,0
    snyk-playground/demo_snyk-transitive-ignore,2021-08-08 04:29:13,False,0
    ```

4) After loading the file into excel or similar it renders like this:
    ![Numbers.app render of CSV](https://github.com/snyk-tech-services/snyk-repo-diff/blob/main/img/table.png?raw=true)

## Support

This script and its contents are provided as a best effort example of how to use Snyk and Github's python sdk's to generate data from both services APIs.

## License
[License: Apache License, Version 2.0](LICENSE)