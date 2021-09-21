import snyk
from snyk.client import SnykClient
import typer
import json
import requests
from github import Github, Repository

from typing import List, Optional
from enum import Enum

app = typer.Typer(add_completion=False)

class FileFormat(str, Enum):
    csv = "csv"
    json = "json"

def retrieve_projects(client: SnykClient, snyk_org_ids: list, origins: list):
    
    projects = []

    with typer.progressbar(snyk_org_ids, label=f"Searching {len(snyk_org_ids)} Snyk Org(s) with {origins} Projects") as typer_org_ids:
        for org_id in typer_org_ids:
            org = client.organizations.get(org_id)
            p_mon = [p for p in org.projects.all() if p.isMonitored and p.origin in origins]
            projects = projects + p_mon

    return projects

def find_projects(repo, projects):


    for p in projects:
        p_sum = {
                'name': p.name,
                'isMonitored': p.isMonitored,
                'lastTestedDate': p.lastTestedDate,
                'browseUrl': p.browseUrl,
                'origin': p.origin
            }

        if p.origin == 'cli' and p.remoteRepoUrl is not None:
            p_sum['remoteRepoUrl'] = p.remoteRepoUrl.replace("http://", "https://").replace('.git','')
        else:
            p_sum['remoteRepoUrl'] = ''
        
        if str(p_sum['name']).startswith(repo['full_name']):
            repo['projects'].append(p_sum)
        elif p_sum['remoteRepoUrl'] in repo['urls']:
            repo['projects'].append(p_sum)

    return repo

def make_csv(repo):
    csv = ['Repository Name,Last Updated,Is Fork,Snyk Project Count']

    for r in repo:
        csv_line = f'{r["full_name"]},{r["updated"]},{r["fork"]},{len(r["projects"])}'
        csv.append(csv_line)

    return "\n".join(csv)


@app.callback(invoke_without_command=True)
def main(snyk_token: str = typer.Option(...,
            prompt="Snyk Token",
            help="Snyk Token with access to the Group whose projects you to want to audit against a Github Organization",
            envvar="SNYK_TOKEN",
        ),
        snyk_group: str = typer.Option(...,
            prompt="Snyk Group",
            help="Only projects associated with the Snyk Group are checked for",
            envvar="SNYK_GROUP",
        ),
        github_token: str = typer.Option(...,
            prompt="GitHub Token",
            help="GitHub Token with read access to the GitHub Org you wish to audit",
            envvar="GITHUB_TOKEN",
        ),
        github_org: str = typer.Option(...,
            prompt="GitHub Org Name",
            help="Name of the GitHub Org whose repositories you want to check",
            envvar="GITHUB_ORG",
        ),
        with_projects: bool = typer.Option( False, "--with-projects",
            help="Include repositories that have projects"
        ),
        out_file: typer.FileTextWrite = typer.Option(...,
            prompt="File to save output to",
            help="Full path to where the output should be saved",
            envvar="REPO_DIFF_OUTPUT",
        ),
        format: FileFormat = typer.Option(FileFormat.csv,
            case_sensitive=False
        ),
        origin: Optional[List[str]] = typer.Option(
            ['github','github-enterprise'],
            help="Specify which Snyk integrations to check for projects"
        )
        ):


    if snyk_token == "BD832F91-A742-49E9-BC1E-411E0C8743EA":
        typer.echo('You have not setup example_secrets.sh correctly')
        typer.echo('Make sure you have saves the file with a valid snyk token')
        typer.Abort()
    
    if snyk_token == "4BB6849A-9D18-4F38-B769-0E2490FA89CA":
        typer.echo('You have not setup example_secrets.sh correctly')
        typer.echo('Make sure you have saves the file with a valid GitHub token')
        typer.Abort()


    client = snyk.SnykClient(snyk_token)

    typer.echo(f"Searching Snyk for Projects from {github_org} repositories")

    try:
        snyk_orgs = client.organizations.all()
    except Exception as e:
        typer.echo(f"Snyk API Error: {e}")
        raise typer.Abort()
        

    snyk_orgs = [ o for o in snyk_orgs if o.group is not None ]

    snyk_org_ids = [o.id for o in snyk_orgs if o.group.id == snyk_group ]

    projects = retrieve_projects(client, snyk_org_ids, origin)
    
    try:
        gh = Github(github_token)
        gh_repos = gh.search_repositories(f'org:{github_org} fork:true')
    except Exception as e:
        typer.echo(f"GitHub API Error: {e}")
        raise typer.Abort()

    repos = []

    with typer.progressbar(gh_repos, length=gh_repos.totalCount, label=f"Checking for Projects from the {gh_repos.totalCount} repos in {github_org}") as typer_gh_repos:
        for r in typer_gh_repos:
            repo = {
                'full_name': r.full_name,
                'urls': [r.ssh_url,r.html_url,r.git_url],
                'updated': str(r.pushed_at),
                'fork': r.fork,
                'projects': []
            }
            repos.append(find_projects(repo, projects))
            typer_gh_repos.update(1)
    
    if not with_projects:
        repos = [r for r in repos if len(r['projects']) == 0]

    typer.echo(f'Formatting and writing results to {out_file.name}')

    try:
        if format.value == 'csv':
            output = make_csv(repos)
        else:
            output = json.dumps(repos, indent=4)
        
        out_file.write(output)

    except Exception as e:
        typer.echo(f"File Write Error: {e}")
        raise typer.Abort()


if __name__ == "__main__":
    app()
