from pathlib import Path
from textwrap import dedent
from copy import deepcopy
from datetime import datetime, MAXYEAR, timezone, timedelta

try:
    import tomllib
except ModuleNotFoundError:
    from pip._vendor import tomli as tomllib

from tabulate import tabulate
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

CONF_FILE = ".config/grok.toml"

# defaults
URL = "https://api.github.com/graphql"


def create_query(org: str, repo: str):
    return dedent(
        """
        {
          repository(owner: \""""
        + org
        + """\", name: \""""
        + repo
        + """\") {
            pullRequests(states: OPEN, first: 30) {
                nodes {
                  ... on PullRequest {
                    createdAt 
                    updatedAt
                    reviewDecision
                    isDraft 
                    number
                    author {
                      login
                    }
                    assignees(first: 5) {
                      nodes {
                      ... on User {
                        login
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """
    )


def do_query(org, repo, key):
    # Select your transport with a defined url endpoint
    transport = RequestsHTTPTransport(
        url=URL,
        verify=True,
        retries=3,
        headers={"Authorization": "bearer " + key},
    )

    # Create a GraphQL client using the defined transport
    client = Client(transport=transport, fetch_schema_from_transport=True)

    # Provide a GraphQL query
    query = gql(create_query(org, repo))

    # Execute the query on the transport
    return client.execute(query)


def format_output(result):
    reviewers = {}
    review_summaries = []
    output = {}
    filtered_keys = ["isDraft", "createdAt"]
    requests = sorted(
        result["repository"]["pullRequests"]["nodes"],
        key=lambda pr: datetime.fromisoformat(pr["createdAt"]),
    )

    # create pull request summary table
    for pull_request in requests:
        pull_request["assignees"] = [
            assignee["login"] for assignee in pull_request.pop("assignees")["nodes"]
        ]
        pull_request["author"] = pull_request.pop("author")["login"]

        # handle unassigned PRs
        if not pull_request["assignees"]:
            if not reviewers.get("unassigned"):
                reviewers["unassigned"] = []
            reviewers["unassigned"].append(deepcopy(pull_request))

        # populate reviewer list for reviewer summary
        for assignee in pull_request["assignees"]:
            if not reviewers.get(assignee):
                reviewers[assignee] = []

            reviewers[assignee].append(deepcopy(pull_request))

        # modify output for pull request summary
        pull_request["updatedAt"] = datetime.fromisoformat(
            pull_request["updatedAt"]
        ).strftime("%y-%m-%d %H:%M")
        pull_request["assignees"] = ", ".join(pull_request.pop("assignees"))
        for key in filtered_keys:
            pull_request.pop(key)
    output["pull_requests"] = deepcopy(requests)

    # create reviewer summary table
    for reviewer, reviews in reviewers.items():
        summary = {}
        review_count = {
            "TOTAL": 0,
            "REVIEW_REQUIRED": 0,
            "APPROVED": 0,
            "CHANGES_REQUESTED": 0,
            None: 0,
        }
        for review in reviews:
            decision = review["reviewDecision"]
            review_count["TOTAL"] += 1
            review_count[decision] += 1
            if not review["isDraft"] and "REVIEW_REQUIRED" == decision:
                summary["oldest waiting review"] = min(
                    summary.pop(
                        "oldest waiting review",
                        datetime(MAXYEAR, 1, 1, tzinfo=timezone(timedelta())),
                    ),
                    datetime.fromisoformat(review["updatedAt"]),
                )
        if summary.get("oldest waiting review"):
            summary["oldest waiting review"] = summary[
                "oldest waiting review"
            ].strftime("%y-%m-%d %H:%M")
        summary["reviewer"] = reviewer
        review_count.pop(None)
        summary.update(review_count)
        review_summaries.append(summary)
    output["reviews"] = review_summaries
    return output


def main():
    with open(Path.home() / CONF_FILE, "rb") as f:
        config = tomllib.load(f)
    default_org = config["system"].get("default_org", "holmanb")
    default_repo = config["system"].get("default_repo", "grok")
    print(f"Querying stats for {default_org}/{default_repo}...")
    result = do_query(default_org, default_repo, config["system"]["auth_key"])
    output = format_output(result)

    print(
        "\n\n".join(
            [
                "Reviewer Summary",
                tabulate(output["reviews"], headers="keys"),
                "Pull Request Summary",
                tabulate(output["pull_requests"], headers="keys"),
            ]
        )
    )


if __name__ == "__main__":
    main()
