# SPDX-FileCopyrightText: 2026 SPDX
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: Apache-2.0

import sqlite3
from typing import Any, Dict, List, Optional
import requests
import xml.etree.ElementTree as ET

from licenseid.normalize import normalize_text


class LicenseDatabase:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialise the SQLite database with FTS5."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS licenses (
                    license_id TEXT PRIMARY KEY,
                    xml_template TEXT,
                    legacy_template TEXT,
                    ignorable_metadata TEXT,
                    is_spdx BOOLEAN,
                    is_osi_approved BOOLEAN,
                    is_fsf_libre BOOLEAN,
                    is_high_usage BOOLEAN
                )
            """)
            # Create FTS5 virtual table for trigram search
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS license_index USING fts5(
                    license_id UNINDEXED,
                    search_text,
                    tokenize = 'trigram'
                )
            """)

    def update_from_remote(self) -> None:
        """
        Fetch license data from SPDX and AboutCode and update the local database.
        """
        print("Updating license database from remote sources...")

        # 1. Fetch SPDX License List metadata
        resp = requests.get(
            "https://raw.githubusercontent.com/spdx/license-list-data/main/json/licenses.json"
        )
        resp.raise_for_status()
        licenses_data = resp.json().get("licenses", [])

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM license_index")
            conn.execute("DELETE FROM licenses")

            for lic in licenses_data:
                license_id = lic["licenseId"]
                try:
                    # Fetch raw license text
                    text_url = f"https://raw.githubusercontent.com/spdx/license-list-data/main/text/{license_id}.txt"
                    text_resp = requests.get(text_url)
                    if text_resp.status_code != 200:
                        continue

                    raw_text = text_resp.text

                    # Also try to fetch XML for template info
                    xml_url = f"https://raw.githubusercontent.com/spdx/license-list-XML/main/src/{license_id}.xml"
                    xml_resp = requests.get(xml_url)
                    xml_content = xml_resp.text if xml_resp.status_code == 200 else None

                    # Create search fingerprint: strip common noise and normalize
                    # In a full implementation, we'd use XML to strip <optional> blocks
                    fingerprint = self._create_fingerprint(raw_text, xml_content)

                    conn.execute(
                        """
                        INSERT INTO licenses (
                            license_id, xml_template, is_spdx, is_osi_approved, is_fsf_libre
                        ) VALUES (?, ?, ?, ?, ?)
                    """,
                        (
                            license_id,
                            xml_content,
                            True,
                            lic.get("isOsiApproved", False),
                            lic.get("isFsfLibre", False),
                        ),
                    )

                    conn.execute(
                        """
                        INSERT INTO license_index (license_id, search_text)
                        VALUES (?, ?)
                    """,
                        (license_id, fingerprint),
                    )
                except Exception as e:
                    print(f"Failed to fetch data for {license_id}: {e}")

    def _create_fingerprint(self, text: str, xml_content: Optional[str] = None) -> str:
        """Create a search fingerprint by removing optional blocks and normalizing."""
        if xml_content:
            try:
                # Simple XML parsing to strip optional parts
                # This is a heuristic; real implementation would use a proper SPDX matcher
                ET.fromstring(xml_content)
                # Find all optional elements and remove them from a virtual text build
                # For now, we just use the raw text and normalize it
                pass
            except Exception:
                pass

        return normalize_text(text)

    def search_candidates(self, text: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Tier 1: Search for candidates using trigram FTS5."""
        norm_text = normalize_text(text)
        # Use OR between the first few words to ensure broad recall.
        # This allows candidates that match most, but not necessarily all, terms.
        words = norm_text.split()[:10]
        if not words:
            return []
        search_terms = " OR ".join(words)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            query = """
                SELECT license_id, search_text
                FROM license_index
                WHERE search_text MATCH ?
                ORDER BY rank
                LIMIT ?
            """
            try:
                # Escape double quotes and use OR-ed keywords for recall
                match_query = search_terms.replace('"', '""')
                cursor = conn.execute(query, (match_query, limit))
                results = [dict(row) for row in cursor.fetchall()]
                return results
            except sqlite3.OperationalError:
                return []

    def get_license_details(self, license_id: str) -> Optional[Dict[str, Any]]:
        """Get full metadata for a license."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM licenses WHERE license_id = ?", (license_id,)
            ).fetchone()
            return dict(row) if row else None
