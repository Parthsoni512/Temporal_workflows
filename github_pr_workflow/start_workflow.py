import argparse
import asyncio
import json
import os
import uuid
from dataclasses import asdict
from pathlib import Path

from temporalio.client import Client

from .models import CreatePullRequestInput, FileChange
from .workflow import CreatePullRequestWorkflow


async def start(request: CreatePullRequestInput) -> str:
    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        namespace=os.environ.get("TEMPORAL_NAMESPACE", "default"),
    )
    return await client.execute_workflow(
        CreatePullRequestWorkflow.run,
        request,
        id=f"github-pr-{uuid.uuid4()}",
        task_queue=os.environ.get("TEMPORAL_TASK_QUEUE", "github-pr-task-queue"),
    )


def load_request(path: Path) -> CreatePullRequestInput:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["files"] = [FileChange(**file) for file in data["files"]]
    return CreatePullRequestInput(**data)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the GitHub pull request workflow")
    parser.add_argument("request", type=Path, help="JSON file describing the changes")
    args = parser.parse_args()
    pull_request_url = asyncio.run(start(load_request(args.request)))
    print(pull_request_url)


if __name__ == "__main__":
    main()