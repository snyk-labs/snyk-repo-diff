```
❯ docker run --rm -v "${PWD}/output":/output -it repo-diff --help
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

```
❯ docker run --rm -v "${PWD}/output":/output -e SNYK_TOKEN -e SNYK_GROUP -e GITHUB_TOKEN -e GITHUB_ORG -it repo-diff --out-file /output/output.csv
Searching Snyk for Projects from snyk-playground repositories
Searching 7 Snyk Org(s) with ('github', 'github-enterprise') Projects  [####################################]  100%          
Checking for Projects from the 27 repos in snyk-playground  [####################################]  100%          
Formatting and writing results to /output/output.csv
```