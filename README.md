# Temporal_workflows

Temporal workflow for creating a GitHub branch, committing supplied files, and
opening a pull request. The GitHub token is read by the activity worker from
`GITHUB_TOKEN`; it is never part of workflow input or Temporal history.

## Requirements

- Python 3.11+
- Docker Compose
- A GitHub personal access token with `Contents: Read and write` and
	`Pull requests: Read and write` access to the target repository

## Run

Start the local Temporal development server and UI:

```bash
docker compose up -d
```

Open the Temporal UI at <http://localhost:8233>. The server listens at
`localhost:7233`, which is the default address used by the worker and workflow
starter. Stop the container with `docker compose down`.

This uses Temporal's development server with its bundled UI and is intended for
local development, not production use.

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

The command waits for completion and prints the pull request URL. The `default`
namespace is used unless `TEMPORAL_NAMESPACE` is set. Set `TEMPORAL_ADDRESS`
and `TEMPORAL_TASK_QUEUE` to override the worker and starter defaults. The
input file contains the content to commit, so do not include secrets in it.