# Temporal_workflows

Temporal workflow for creating a GitHub branch, committing supplied files, and
opening a pull request. The GitHub token is read by the activity worker from
`GITHUB_TOKEN`; it is never part of workflow input or Temporal history.

## Requirements

- Python 3.11+
- A running Temporal server (for local development, `temporal server start-dev`)
- A GitHub personal access token with `Contents: Read and write` and
	`Pull requests: Read and write` access to the target repository

## Run

Install the package and set the token in the worker's environment:

```bash
python -m pip install -e .
export GITHUB_TOKEN=github_pat_...
```

Start the Temporal worker in one terminal:

```bash
python -m github_pr_workflow.worker
```

Create `request.json` with the repository and changes to commit:

```json
{
	"owner": "your-org",
	"repo": "your-repo",
	"base_branch": "main",
	"branch_name": "automation/update-readme",
	"commit_message": "Update project notes",
	"pull_request_title": "Update project notes",
	"pull_request_body": "Automated update.",
	"files": [
		{"path": "notes.txt", "content": "Updated by a Temporal workflow.\n"}
	]
}
```

Start the workflow from another terminal:

```bash
python -m github_pr_workflow.start_workflow request.json
```

The command waits for completion and prints the pull request URL. Temporal's
local development server uses `localhost:7233` and the `default` namespace by
default. Set `TEMPORAL_ADDRESS`, `TEMPORAL_NAMESPACE`, and `TEMPORAL_TASK_QUEUE`
to override those defaults. The input file contains the content to commit, so
do not include secrets in it.