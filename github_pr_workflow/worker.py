import asyncio
import os

from temporalio.client import Client
from temporalio.worker import Worker

from .activities import commit_files, create_branch, create_pull_request
from .workflow import CreatePullRequestWorkflow


async def main() -> None:
    if not os.environ.get("GITHUB_TOKEN"):
        raise RuntimeError("Set GITHUB_TOKEN in the activity worker environment")

    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        namespace=os.environ.get("TEMPORAL_NAMESPACE", "default"),
    )
    worker = Worker(
        client,
        task_queue=os.environ.get("TEMPORAL_TASK_QUEUE", "github-pr-task-queue"),
        workflows=[CreatePullRequestWorkflow],
        activities=[create_branch, commit_files, create_pull_request],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())