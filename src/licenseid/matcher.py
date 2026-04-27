# SPDX-FileCopyrightText: 2026 SPDX
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: Apache-2.0

import os
import shutil
from typing import Any, Dict, List, Union

from rapidfuzz import fuzz

from licenseid.database import LicenseDatabase
from licenseid.normalize import normalize_text


class AggregatedLicenseMatcher:
    def __init__(self, db_path: str, enable_java: bool = False):
        self.db = LicenseDatabase(db_path)
        self.enable_java = enable_java
        self.jar_path = os.getenv("SPDX_TOOLS_JAR")
        self.has_java = shutil.which("java") is not None

    def match(self, data: Union[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Identify license text and return ranked matches.
        """
        if isinstance(data, str):
            data = {"text": data, "only_spdx": True, "only_common": False}

        text = data.get("text", "")
        only_spdx = data.get("only_spdx", True)
        only_common = data.get("only_common", False)
        exclude_list = data.get("exclude", [])
        hint_list = data.get("hint", [])
        enable_java = data.get("enable_java", self.enable_java)

        # Tier 1: Broad Recall (SQLite Trigram)
        candidates = self.db.search_candidates(text)

        # Filter candidates based on metadata
        filtered_candidates = []
        for cand in candidates:
            license_id = cand["license_id"]
            if license_id in exclude_list:
                continue

            details = self.db.get_license_details(license_id)
            if not details:
                continue

            if only_spdx and not details.get("is_spdx"):
                continue
            if only_common and not details.get("is_high_usage"):
                # Fallback to OSI/FSF approval status if high_usage flag is missing
                if not (details.get("is_osi_approved") or details.get("is_fsf_libre")):
                    continue

            filtered_candidates.append(cand)

        # Force-include hints
        candidate_ids = {c["license_id"] for c in filtered_candidates}
        for h_id in hint_list:
            if h_id not in candidate_ids:
                details = self.db.get_license_details(h_id)
                if details:
                    # Append hinted license for precision ranking
                    filtered_candidates.append({"license_id": h_id, "search_text": ""})

        # Tier 2: Precision Ranking (RapidFuzz Token Set Ratio)
        # We compare the input text with the search_text (normalized fingerprint)
        norm_input = normalize_text(text)
        ranked = []
        for cand in filtered_candidates:
            # If search_text is empty (e.g. from hint), try to fetch it
            search_text = cand.get("search_text") or ""

            # Token Set Ratio is good for reordered paragraphs and minor noise
            score = fuzz.token_set_ratio(norm_input, search_text) / 100.0
            ranked.append({"license_id": cand["license_id"], "score": score})

        ranked.sort(key=lambda x: x["score"], reverse=True)

        # Tier 3: Optional Java Consultant
        if (
            enable_java
            and self.has_java
            and self.jar_path
            and os.path.exists(self.jar_path)
            and ranked
        ):
            return self._consult_java(text, ranked)

        return ranked

    def _ensure_jvm(self) -> None:
        """Ensure the JVM is started with the tools-java JAR."""
        try:
            import jpype
        except ImportError:
            raise ImportError(
                "JPype1 is required for Java validation. "
                "Install it with 'pip install licenseid[java]'"
            )

        if not jpype.isJVMStarted():
            # Start JVM with daemon thread support and string conversion disabled
            jpype.startJVM(classpath=[self.jar_path], convertStrings=False)
            # Initialize SPDX Model Factory once
            SpdxModelFactory = jpype.JClass("org.spdx.library.SpdxModelFactory")
            SpdxModelFactory.init()

    def _consult_java(
        self, text: str, ranked: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Consult the tools-java MatchingStandardLicenses logic via JPype.
        """
        try:
            import jpype
        except ImportError:
            # If enable_java was True but JPype is missing, we already checked in match()
            # but being safe here too.
            return ranked

        self._ensure_jvm()

        # Reliable thread attach/detach pattern
        JThread = jpype.JClass("java.lang.Thread")
        JThread.attachAsDaemon()
        try:
            LicenseCompareHelper = jpype.JClass(
                "org.spdx.utility.compare.LicenseCompareHelper"
            )

            # matchingStandardLicenseIdsWithinText returns a java.util.List<String>
            java_matches_list = (
                LicenseCompareHelper.matchingStandardLicenseIdsWithinText(text)
            )
            # convertStrings=False requires manual conversion
            java_matches = {str(m) for m in java_matches_list}

            # Boost scores for Java-verified matches
            for r in ranked:
                if r["license_id"] in java_matches:
                    r["score"] = 1.0  # Perfect match if Java verifies
                    r["java_verified"] = True
        except Exception:
            # Handle or log exception
            pass
        finally:
            JThread.detach()

        # Re-sort matches by boosted score
        ranked.sort(key=lambda x: x["score"], reverse=True)
        return ranked
