from dataclasses import dataclass
import os
from typing import Optional, Tuple
from urllib.parse import urlparse


@dataclass
class Repository:
    owner: str
    repo: str
    reference: Optional[str] = None
    branch: Optional[str] = None

    sha: Optional[str] = None

    def __str__(self) -> str:
        return f"{self.owner}/{self.repo}"

    def __repr__(self) -> str:
        return self.__str__()

    def display(self):
        if self.reference:
            return f"{self.owner}/{self.repo}@{self.reference}"
        return f"{self.owner}/{self.repo}"

    @staticmethod
    def parseRepository(name: str) -> "Repository":
        ref = None
        if "@" in name:
            name, ref = name.split("@", 1)
        owner, repo = name.split("/", 1)
        return Repository(owner, repo, ref)


class GitHub:
    repository: Optional[Repository] = None
    token: Optional[str] = None

    # URLs
    instance: str = "https://github.com"
    api_rest: str = "https://api.github.com"
    api_graphql: str = "https://api.github.com/graphql"

    @staticmethod
    def init(
        repository: Optional[str] = None,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
        reference: Optional[str] = None,
        branch: Optional[str] = None,
        token: Optional[str] = os.environ.get("GITHUB_TOKEN"),
        instance: Optional[str] = None,
    ) -> None:
        if repository:
            GitHub.repository = Repository.parseRepository(repository)
        elif owner and repo:
            GitHub.repository = Repository(owner, repo)

        if GitHub.repository:
            if reference:
                GitHub.repository.reference = reference
            if branch:
                GitHub.repository.branch = branch

        GitHub.token = token
        # instance
        if instance:
            GitHub.instance = instance
            GitHub.api_rest, GitHub.api_graphql = GitHub.parseInstance(instance)

        return

    @staticmethod
    def parseInstance(instance: str) -> Tuple[str, str]:
        url = urlparse(instance)

        # GitHub Cloud (.com)
        if url.netloc == "github.com":
            api = url.scheme + "://api." + url.netloc
            return (api, f"{api}/graphql")
        # GitHub Ent Server
        api = url.scheme + "://" + url.netloc + "/api"

        return (api, f"{api}/graphql")
