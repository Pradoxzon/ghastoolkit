import os
import json
from typing import List, Optional
from dataclasses import dataclass, field

from semantic_version import SimpleSpec, Version

from ghastoolkit.octokit.octokit import OctoItem


def parseVersion(data: str) -> str:
    """Parse Version to help semantic_version process the version."""
    stack = data.split(".")
    if len(stack) == 1:
        return f"{data}.0.0"
    elif len(stack) == 2:
        return f"{data}.0"
    return data


@dataclass
class AdvisoryAffect:
    """Advisory Affected."""

    ecosystem: str
    """Ecosystem / Dependency Manager / PURL type"""
    package: str
    """Package Full Name ([namespace +] name"""

    introduced: Optional[str] = None
    """Introduced Version"""
    fixed: Optional[str] = None
    """Fixed Version"""

    package_dependency: Optional["Dependency"] = None

    def __post_init__(self):
        self.ecosystem = self.ecosystem.lower()
        # load package as dependency
        from ghastoolkit import Dependency

        # HACK can we do this a better way?
        if self.ecosystem in ["maven", "nuget"]:
            namespace, name = self.package.rsplit(".", 1)
        else:
            namespace = None
            name = self.package

        self.package_dependency = Dependency(name, namespace, manager=self.ecosystem)

        if self.introduced:
            self.introduced = parseVersion(self.introduced)
        if self.fixed:
            self.fixed = parseVersion(self.fixed)

    @staticmethod
    def loadAffect(data: dict) -> "AdvisoryAffect":
        """Load affects from data.

        https://github.com/github/advisory-database
        """
        # get introduced and fixed versions
        events = data.get("ranges", [{}])[0].get("events", [])
        introduced = None
        fixed = None
        for event in events:
            if event.get("introduced"):
                introduced = event.get("introduced")
            if event.get("fixed"):
                fixed = event.get("fixed")

        adaff = AdvisoryAffect(
            data.get("package", {}).get("ecosystem", "NA").lower(),
            data.get("package", {}).get("name", "NA"),
            introduced=introduced,
            fixed=fixed,
        )
        return adaff

    def check(self, dependency: "Dependency") -> bool:
        """Check to see in the dependency is affected by the advisory."""

        from ghastoolkit import Dependency

        if not isinstance(dependency, Dependency):
            raise Exception(f"Unknown type provided :: {type(dependency)}")
        # None checks
        if not self.package_dependency or not dependency.version:
            return False
        # manager / ecosystem
        if dependency.manager != self.ecosystem:
            return False
        # name
        if dependency.name != self.package_dependency.name:
            return False
        return self.checkVersion(dependency.version)

    def checkVersion(self, version: str) -> bool:
        """Check version data."""
        if not self.introduced or not self.fixed:
            return False
        # print(f"- {self.introduced} > {parseVersion(version)} < {self.fixed}")
        spec = SimpleSpec(f">={self.introduced},<{self.fixed}")
        return Version(parseVersion(version)) in spec


@dataclass
class Advisory(OctoItem):
    """GitHub Advisory."""

    ghsa_id: str
    """GitHub Security Advisory Identifier"""
    severity: str
    """Severity level"""

    aliases: List[str] = field(default_factory=list)
    """List of aliases (CVEs)"""

    summary: Optional[str] = None
    """Summary / Description of the advisory"""
    url: Optional[str] = None
    """Reference URL"""

    cwes: List[str] = field(default_factory=list)
    """List of CWEs"""

    affected: List[AdvisoryAffect] = field(default_factory=list)
    """Affected versions"""

    @staticmethod
    def load(path: str) -> "Advisory":
        """Load Advisory from path using GitHub Advisory Spec."""
        if not os.path.exists(path):
            raise Exception(f"Advisory path does not exist")

        _, ext = os.path.splitext(path)
        if ext == ".json":
            return Advisory.loadJson(path)

        raise Exception("Unsupported Advisory file type")

    @staticmethod
    def loadJson(path: str) -> "Advisory":
        """Load Advisory from JSON file."""
        with open(path, "r") as handle:
            data = json.load(handle)

        affected = []
        for affect in data.get("affected", []):
            affected.append(AdvisoryAffect.loadAffect(affect))

        advisory = Advisory(
            data.get("id", "NA"),
            data.get("database_specific", {}).get("severity", "NA").lower(),
            aliases=data.get("aliases", []),
            summary=data.get("summary"),
            affected=affected,
        )
        return advisory

    def check(self, dependency: "Dependency") -> Optional["Advisory"]:
        """Check if dependency is affected by advisory."""
        for affect in self.affected:
            if affect.check(dependency):
                return self
        return


class Advisories:
    """GitHub Advisory List."""

    def __init__(self) -> None:
        """Initialise Advisories."""
        self.advisories: List[Advisory] = []

    def loadAdvisories(self, path: str):
        """Load a single file or folder of advisories."""
        if not os.path.exists(path):
            raise Exception("Advisories path does not exist")
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for file in files:
                    _, ext = os.path.splitext(file)
                    if ext in [".json"]:
                        fpath = os.path.join(root, file)
                        self.loadAdvisory(fpath)
        else:
            self.loadAdvisory(path)

    def loadAdvisory(self, path: str):
        """Load file with an advisory."""
        if not os.path.exists(path):
            raise Exception(f"Path does not exist")
        self.advisories.append(Advisory.load(path))

    def find(self, search: str) -> Optional[Advisory]:
        """Find by id or aliases."""
        for advisory in self.advisories:
            if advisory.ghsa_id == search:
                return advisory
            if search in advisory.aliases:
                return advisory
        return

    def check(self, dependency: "Dependency") -> List[Advisory]:
        """Check if dependency is affected by any advisory in the list of advisories."""
        results = []
        for a in self.advisories:
            result = a.check(dependency)
            if result:
                results.append(result)

        return results

    def append(self, advisory: Advisory):
        """Append advisory."""
        if not isinstance(advisory, Advisory):
            raise Exception(f"Non-Advisory type tring to be appended")
        self.advisories.append(advisory)

    def __len__(self) -> int:
        """To String."""
        return len(self.advisories)
