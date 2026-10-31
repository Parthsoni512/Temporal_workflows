from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from .activities import commit_files, create_branch, create_pull_request
    from .models import CreatePullRequestInput


@workflow.defn
class CreatePullRequestWorkflow:
    @workflow.run
    async def run(self, request: CreatePullRequestInput) -> str:
        if request.branch_name == request.base_branch:
            raise ValueError("The new branch must differ from the base branch")
        if not request.files:
            raise ValueError("At least one file is required")

        activity_options = {
            "start_to_close_timeout": timedelta(minutes=2),
            "retry_policy": RetryPolicy(
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=30),
                maximum_attempts=5,
            ),
        }
        await workflow.execute_activity(
            create_branch,
            args=[request.owner, request.repo, request.base_branch, request.branch_name],
            **activity_options,
        )
        await workflow.execute_activity(
            commit_files,
            args=[
                request.owner,
                request.repo,
                request.branch_name,
                request.commit_message,
                [{"path": file.path, "content": file.content} for file in request.files],
                workflow.info().workflow_id,
            ],
            **activity_options,
        )
        return await workflow.execute_activity(
            create_pull_request,
            args=[
                request.owner,
                request.repo,
                request.base_branch,
                request.branch_name,
                request.pull_request_title,
                request.pull_request_body,
            ],
            **activity_options,
        )