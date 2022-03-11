import snyk
from snyk.client import SnykClient
import typer
import json
from github import Github
import gitlab

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


def get_repos(origin: Origin, scm_token: str, scm_org: str = None, scm_url: str = None):

    if origin.value == "github" or origin.value == "github-enterprise":
        try:
            if scm_url:
                gh = Github(login_or_token=scm_token, base_url=scm_url)
            else:
                gh = Github(login_or_token=scm_token)

            repos = normalize_github(gh.search_repositories(f"org:{scm_org} fork:true"))
        except Exception as e:
            typer.echo(f"GitHub API Error: {e}")
            raise typer.Abort()
    elif origin.value == "gitlab":
        try:
            if scm_url:
                gl = gitlab.Gitlab(
                    url=scm_url,
                    private_token=scm_token,
                )
            else:
                gl = gitlab.Gitlab(private_token=scm_token)

            g_id = gl.groups.list(search=scm_org)[0].id
            group = gl.groups.get(g_id)
            repos = normalize_gitlab(group.projects.list(include_subgroups=True))

        except Exception as e:
            typer.echo(f"GitLab API Error: {e}")
            raise typer.Abort()
    else:
        typer.echo("Invalid SCM name provided")
        raise typer.Abort()

    return repos


def normalize_gitlab(repos) -> list:

    new_repos = []

    for r in repos:
        repo = {
            "full_name": r.path_with_namespace,
            "urls": [r.ssh_url_to_repo, r.http_url_to_repo],
            "updated": str(r.last_activity_at),
            "projects": [],
        }
        new_repos.append(repo)

    return new_repos


def normalize_github(repos) -> list:

    new_repos = []

    for r in repos:
        repo = {
            "full_name": r.full_name,
            "urls": [r.ssh_url, r.html_url, r.git_url],
            "updated": str(r.pushed_at),
            "fork": r.fork,
            "projects": [],
        }
        new_repos.append(repo)

    return new_repos


def has_forks(fork_count: int = 0) -> bool:
    return bool(fork_count != 0)


def get_targets(
    self,
    client: SnykClient,
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

    targets = client.get_v3_pages(path, params)

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
            p_sum["remoteUrl"] = p.remoteUrl.replace("http://", "https://").replace(
                ".git", ""
            )
        else:
            p_sum["remoteUrl"] = ""

        if str(p_sum["name"]).startswith(repo["full_name"]):
            repo["projects"].append(p_sum)
        elif p_sum["remoteUrl"] in repo["urls"]:
            repo["projects"].append(p_sum)

    return repo


def make_csv(repo, origins):

    if origins in ("github", "github-enterprise"):
        csv = ["Repository Name,Last Updated,Is Fork,Snyk Project Count"]

        for r in repo:
            csv_line = (
                f'{r["full_name"]},{r["updated"]},{r["fork"]},{len(r["projects"])}'
            )
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
    scm_url: str = typer.Option(
        None,
        help="Provide url as https://gitlab.example.com etc",
        envvar="SCM_URL",
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

    print(scm_url)

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

    # this connects to a single github or gitlab group/org and gets all the repositories
    the_repos = get_repos(origin, scm_token, scm_org, scm_url)

    repos = []

    with typer.progressbar(
        the_repos,
        length=len(the_repos),
        label=f"Checking for Projects from the {len(the_repos)} repos in {scm_org}",
    ) as typer_the_repos:
        for repo in typer_the_repos:
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
