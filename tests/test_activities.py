import json
import unittest

import httpx

from github_pr_workflow.activities import GitHubClient


class GitHubClientTests(unittest.TestCase):
    def make_client(self, handler):
        github = GitHubClient("test-token")
        github._client.close()
        github._client = httpx.Client(
            base_url="https://api.github.com",
            headers={"Authorization": "Bearer test-token"},
            transport=httpx.MockTransport(handler),
        )
        self.addCleanup(github._client.close)
        return github

    def test_create_branch_uses_base_ref_sha(self):
        requests = []

        def handler(request):
            requests.append(request)
            if request.method == "GET":
                return httpx.Response(200, json={"object": {"sha": "base-sha"}})
            return httpx.Response(201, json={})

        github = self.make_client(handler)
        github.create_branch("acme", "demo", "main", "feature/change")

        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[1].url.path, "/repos/acme/demo/git/refs")
        self.assertEqual(json.loads(requests[1].content), {
            "ref": "refs/heads/feature/change",
            "sha": "base-sha",
        })

    def test_commit_files_creates_one_commit_for_all_files(self):
        requests = []

        def handler(request):
            requests.append(request)
            path = request.url.path
            if request.method == "GET" and path.endswith("/git/ref/heads/feature"):
                return httpx.Response(200, json={"object": {"sha": "parent-sha"}})
            if request.method == "GET":
                return httpx.Response(
                    200,
                    json={"message": "previous", "tree": {"sha": "parent-tree"}},
                )
            if path.endswith("/git/blobs"):
                return httpx.Response(201, json={"sha": "blob-sha"})
            if path.endswith("/git/trees"):
                return httpx.Response(201, json={"sha": "tree-sha"})
            if path.endswith("/git/commits"):
                return httpx.Response(201, json={"sha": "commit-sha"})
            return httpx.Response(200, json={})

        github = self.make_client(handler)
        commit_sha = github.commit_files(
            "acme",
            "demo",
            "feature",
            "Add two files",
            [
                {"path": "one.txt", "content": "one"},
                {"path": "two.txt", "content": "two"},
            ],
            "workflow-123",
        )

        commit_requests = [request for request in requests if request.url.path.endswith("/git/commits")]
        self.assertEqual(commit_sha, "commit-sha")
        self.assertEqual(len(commit_requests), 1)
        self.assertEqual(commit_requests[0].headers["Authorization"], "Bearer test-token")
        self.assertIn("Temporal-Workflow-ID: workflow-123", commit_requests[0].content.decode())
        tree_request = next(request for request in requests if request.url.path.endswith("/git/trees"))
        self.assertEqual(len(json.loads(tree_request.content)["tree"]), 2)

    def test_create_pull_request_returns_existing_pr_after_retry(self):
        def handler(request):
            if request.method == "POST":
                return httpx.Response(422, json={"message": "A pull request already exists"})
            return httpx.Response(200, json=[{"html_url": "https://github.com/acme/demo/pull/7"}])

        github = self.make_client(handler)
        url = github.create_pull_request(
            "acme", "demo", "main", "feature", "Change", "Automated change"
        )

        self.assertEqual(url, "https://github.com/acme/demo/pull/7")


if __name__ == "__main__":
    unittest.main()