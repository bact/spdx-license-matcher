# SPDX-FileCopyrightText: 2026 SPDX
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: Apache-2.0

import os
from licenseid.matcher import AggregatedLicenseMatcher

def test_matcher_detects_bundled_jar():
    """Verify that the matcher correctly identifies the jar in the tests directory."""
    # The conftest.py fixture should have set SPDX_TOOLS_JAR
    jar_path = os.getenv("SPDX_TOOLS_JAR")
    assert jar_path is not None
    assert jar_path.endswith("tests/tool.jar")
    assert os.path.exists(jar_path)

    # Initialize matcher (requires a DB path, using a dummy one)
    matcher = AggregatedLicenseMatcher("dummy.db")
    assert matcher.jar_path == jar_path
    # Note: has_java depends on 'java' being in the system PATH
