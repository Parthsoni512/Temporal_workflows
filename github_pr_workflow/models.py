from dataclasses import dataclass


@dataclass
class FileChange:
    path: str
    content: str


@dataclass
class CreatePullRequestInput:
    owner: str
    repo: str
    base_branch: str
    branch_name: str
    commit_message: str
    pull_request_title: str
    pull_request_body: str
    files: list[FileChange]