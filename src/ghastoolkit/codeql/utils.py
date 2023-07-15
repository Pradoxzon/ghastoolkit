import logging
import os
import subprocess
from typing import Optional


logger = logging.getLogger("ghastoolkit.codeql")


def findCodeBinary() -> Optional[list[str]]:
    locations = [["codeql"], ["gh", "codeql"], ["/usr/bin/codeql/codeql"]]

    for location in locations:
        try:
            cmd = location + ["version"]
            with open(os.devnull, "w") as null:
                subprocess.check_call(cmd, stdout=null, stderr=null)

            return location
        except Exception as err:
            logger.debug(f"Failed to find codeql :: {err}")

    return
