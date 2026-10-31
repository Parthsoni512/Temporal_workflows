import os
from urllib.parse import quote

import httpx
from temporalio import activity


class GitHubClient:
    def __init__(self, token: str) -> None:
        self._client = httpx.Client(
            base_url="https://api.github.com",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30,
        )

    def __enter__(self) -> "GitHubClient":
        return self

    def __exit__(self, *_: object) -> None:
        self._client.close()

    @classmethod
    def from_environment(cls) -> "GitHubClient":
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            raise RuntimeError("GITHUB_TOKEN must be set on the activity worker")
        return cls(token)

    @staticmethod
    def _repo_path(owner: str, repo: str) -> str:
        return f"/repos/{quote(owner, safe='')}/{quote(repo, safe='')}"

    def _request(self, method: str, path: str, **kwargs: object) -> object:
        response = self._client.request(method, path, **kwargs)
        response.raise_for_status()
        if response.content:
            return response.json()
        return None

    def create_branch(self, owner: str, repo: str, base_branch: str, branch_name: str) -> None:
        repository = self._repo_path(owner, repo)
        base_ref = self._request(
            "GET", f"{repository}/git/ref/heads/{quote(base_branch, safe='/')}"
        )
        base_sha = base_ref["object"]["sha"]
        response = self._client.post(
            f"{repository}/git/refs",
            json={"ref": f"refs/heads/{branch_name}", "sha": base_sha},
        )
        if response.is_success:
            return
        if response.status_code == 422:
            current_ref = self._request(
                "GET", f"{repository}/git/ref/heads/{quote(branch_name, safe='/')}"
            )
            if current_ref["object"]["sha"] == base_sha:
                return
        response.raise_for_status()

    def commit_files(
        self,
        owner: str,
        repo: str,
        branch_name: str,
        commit_message: str,
        files: list[dict[str, str]],
        workflow_id: str,
    ) -> str:
        repository = self._repo_path(owner, repo)
        branch_path = f"{repository}/git/ref/heads/{quote(branch_name, safe='/')}"
        branch_ref = self._request("GET", branch_path)
        parent_sha = branch_ref["object"]["sha"]
        parent_commit = self._request("GET", f"{repository}/git/commits/{parent_sha}")
        marker = f"Temporal-Workflow-ID: {workflow_id}"
        if marker in parent_commit["message"]:
            return parent_sha

        tree_entries = []
        for file in files:
            blob = self._request(
                "POST",
                f"{repository}/git/blobs",
                json={"content": file["content"], "encoding": "utf-8"},
            )
            tree_entries.append(
                {
                    "path": file["path"],
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob["sha"],
                }
            )

        tree = self._request(
            "POST",
            f"{repository}/git/trees",
            json={"base_tree": parent_commit["tree"]["sha"], "tree": tree_entries},
        )
        message = f"{commit_message.rstrip()}\n\n{marker}"
        commit = self._request(
            "POST",
            f"{repository}/git/commits",
            json={"message": message, "tree": tree["sha"], "parents": [parent_sha]},
        )
        self._request("PATCH", branch_path, json={"sha": commit["sha"], "force": False})
        return commit["sha"]

    def create_pull_request(
        self,
        owner: str,
        repo: str,
        base_branch: str,
        branch_name: str,
        title: str,
        body: str,
    ) -> str:
        repository = self._repo_path(owner, repo)
        response = self._client.post(
            f"{repository}/pulls",
            json={"title": title, "head": branch_name, "base": base_branch, "body": body},
        )
        if response.is_success:
            return response.json()["html_url"]
        if response.status_code == 422:
            existing = self._request(
                "GET",
                f"{repository}/pulls",
                params={"head": f"{owner}:{branch_name}", "base": base_branch, "state": "open"},
            )
            if existing:
                return existing[0]["html_url"]
        response.raise_for_status()


@activity.defn
def create_branch(owner: str, repo: str, base_branch: str, branch_name: str) -> None:
    with GitHubClient.from_environment() as github:
        github.create_branch(owner, repo, base_branch, branch_name)


@activity.defn
def commit_files(
    owner: str,
    repo: str,
    branch_name: str,
    commit_message: str,
    files: list[dict[str, str]],
    workflow_id: str,
) -> str:
    with GitHubClient.from_environment() as github:
        return github.commit_files(
            owner, repo, branch_name, commit_message, files, workflow_id
        )


@activity.defn
def create_pull_request(
    owner: str,
    repo: str,
    base_branch: str,
    branch_name: str,
    title: str,
    body: str,
) -> str:
    with GitHubClient.from_environment() as github:
        return github.create_pull_request(
            owner, repo, base_branch, branch_name, title, body
        )