import snyk
from snyk.client import SnykClient
from snykv3 import SnykV3Client
import typer
import json
import requests
from github import Github, Repository
import gitlab

from typing import List, Optional
from enum import Enum

app = typer.Typer(add_completion=False)


class FileFormat(str, Enum):
    csv = "csv"
    json = "json"


class Origin(str, Enum):
    github = "github"
    github_enterprise = "github-enterprise"
    gitlab = "gitlab"


def retrieve_projects(client: SnykClient, snyk_org_ids: list, origins: list):

    projects = []

    with typer.progressbar(
        snyk_org_ids,
        label=f"Searching {len(snyk_org_ids)} Snyk Org(s) with {origins} Projects",
    ) as typer_org_ids:
        for org_id in typer_org_ids:
            org = client.organizations.get(org_id)
            p_mon = [
                p for p in org.projects.all() if p.isMonitored and p.origin in origins
            ]
            projects = projects + p_mon

    return projects


def get_repos(origin: Origin, scm_token: str, scm_org: str = None):

    if origin.value == "github":
        try:
            gh = Github(scm_token)
            repos = gh.search_repositories(f"org:{scm_org} fork:true")
        except Exception as e:
            typer.echo(f"GitHub API Error: {e}")
            raise typer.Abort()
    elif origin.value == "gitlab":
        try:
            gl = gitlab.Gitlab(private_token=scm_token)

            groups = gl.groups.list(search=scm_org)

            for g in groups:
                print(g)

            g_id = gl.groups.list(search=scm_org)[0].id
            group = gl.groups.get(g_id)
            repos = group.projects.list(include_subgroups=True)
            print(len(repos))
            for r in repos:
                print(r.attributes)
        except Exception as e:
            typer.echo(f"GitLab API Error: {e}")
            raise typer.Abort()
    else:
        typer.echo("Invalid SCM name provided")
        raise typer.Abort()

    return repos


def get_targets(
    self,
    client: SnykV3Client,
    origin: str = None,
    exclude_empty: bool = True,
    limit: int = 100,
):
    """
    Retrieves all the targets from this org object, using the provided client
    Optionally matches on 'origin'
    """

    params = {"origin": origin, "limit": limit, "excludeEmpty": exclude_empty}

    path = f"orgs/{self.id}/targets"

    targets = client.get_all_pages(path, params)

    print(targets)

    return targets


def find_projects(repo, projects):

    for p in projects:
        p_sum = {
            "name": p.name,
            "isMonitored": p.isMonitored,
            "lastTestedDate": p.lastTestedDate,
            "browseUrl": p.browseUrl,
            "origin": p.origin,
        }

        if p.origin == "cli" and p.remoteUrl is not None:
            p_sum["remoteUrl"] = p.remoteUrl.replace(
                "http://", "https://"
            ).replace(".git", "")
        else:
            p_sum["remoteUrl"] = ""

        if str(p_sum["name"]).startswith(repo["full_name"]):
            repo["projects"].append(p_sum)
        elif p_sum["remoteUrl"] in repo["urls"]:
            repo["projects"].append(p_sum)

    return repo


def make_csv(repo, origins):

    if origins in ("github","github-enterprise"):
        csv = ["Repository Name,Last Updated,Is Fork,Snyk Project Count"]

        for r in repo:
            csv_line = f'{r["full_name"]},{r["updated"]},{r["fork"]},{len(r["projects"])}'
            csv.append(csv_line)

        return "\n".join(csv)
    else:
        csv = ["Repository Name,Last Updated,Snyk Project Count"]

        for r in repo:
            csv_line = f'{r["full_name"]},{r["updated"]},{len(r["projects"])}'
            csv.append(csv_line)

        return "\n".join(csv)


@app.callback(invoke_without_command=True)
def main(
    snyk_token: str = typer.Option(
        ...,
        prompt="Snyk Token",
        help="Snyk Token with access to the Group whose projects you to want to audit against a Github Organization",
        envvar="SNYK_TOKEN",
    ),
    snyk_group: str = typer.Option(
        ...,
        prompt="Snyk Group",
        help="Only projects associated with the Snyk Group are checked for",
        envvar="SNYK_GROUP",
    ),
    scm_token: str = typer.Option(
        ...,
        prompt="SCM Access Token",
        help="Access Token to the SCM platform you wish to audit (GitHub and GitLab currently supported)",
        envvar="SCM_TOKEN",
    ),
    scm_org: str = typer.Option(
        ...,
        prompt="SCM Org/Group Name",
        help="Name of the GitHub Org or GitLab Group whose repos you want to check against",
        envvar="SCM_ORG",
    ),
    with_projects: bool = typer.Option(
        False, "--with-projects", help="Include repositories that have projects"
    ),
    out_file: typer.FileTextWrite = typer.Option(
        ...,
        prompt="File to save output to",
        help="Full path to where the output should be saved",
        envvar="REPO_DIFF_OUTPUT",
    ),
    format: FileFormat = typer.Option(FileFormat.csv, case_sensitive=False),
    origin: Origin = typer.Option(Origin.github, case_sensitive=False),
):

    if snyk_token == "BD832F91-A742-49E9-BC1E-411E0C8743EA":
        typer.echo("You have not setup example_secrets.sh correctly")
        typer.echo("Make sure you have saves the file with a valid snyk token")
        typer.Abort()

    if snyk_token == "4BB6849A-9D18-4F38-B769-0E2490FA89CA":
        typer.echo("You have not setup example_secrets.sh correctly")
        typer.echo("Make sure you have saves the file with a valid GitHub token")
        typer.Abort()

    client = snyk.SnykClient(snyk_token)

    typer.echo(f"Searching Snyk for Projects from {scm_org} repositories")

    try:
        snyk_orgs = client.organizations.all()
    except Exception as e:
        typer.echo(f"Snyk API Error: {e}")
        raise typer.Abort()

    snyk_orgs = [o for o in snyk_orgs if o.group is not None]

    snyk_org_ids = [o.id for o in snyk_orgs if o.group.id == snyk_group]

    # This recursively gets project information for every org
    projects = retrieve_projects(client, snyk_org_ids, origin)

    # just to sanity check - remove in final build
    print(origin)

    scm = origin.value

    # sanity check
    print(scm)

    # this connects to a single github or gitlab group/org and gets all the repositories
    the_repos = get_repos(origin, scm_token, scm_org)

    print(the_repos)

    repos = []

    with typer.progressbar(
        the_repos,
        length=len(the_repos),
        label=f"Checking for Projects from the {len(the_repos)} repos in {scm_org}",
    ) as typer_the_repos:
        for r in typer_the_repos:
            repo = {
                "full_name": r.path_with_namespace,
                "urls": [r.ssh_url_to_repo, r.http_url_to_repo],
                "updated": str(r.last_activity_at),
                "projects": [],
            }
            repos.append(find_projects(repo, projects))
            typer_the_repos.update(1)

    if not with_projects:
        repos = [r for r in repos if len(r["projects"]) == 0]

    typer.echo(f"Formatting and writing results to {out_file.name}")

    try:
        if format.value == "csv":
            output = make_csv(repos, {origin})
        else:
            output = json.dumps(repos, indent=4)

        out_file.write(output)

    except Exception as e:
        typer.echo(f"File Write Error: {e}")
        raise typer.Abort()


if __name__ == "__main__":
    app()
    