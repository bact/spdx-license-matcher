# SPDX-FileCopyrightText: 2026 SPDX
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: Apache-2.0

import sqlite3
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests

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
                    licenseId TEXT PRIMARY KEY,
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
                    licenseId UNINDEXED,
                    search_text,
                    tokenize = 'trigram'
                )
            """)

    def update_from_remote(self) -> None:
        """
        Fetch license data from SPDX and AboutCode and update the local database.
        
        This builds the initial index by fetching the canonical SPDX license list
        and the corresponding raw text files.
        """
        print("Updating license database from remote sources...")
        
        # 1. Fetch SPDX License List
        resp = requests.get("https://raw.githubusercontent.com/spdx/license-list-data/main/json/licenses.json")
        resp.raise_for_status()
        licenses_data = resp.json().get("licenses", [])

        with sqlite3.connect(self.db_path) as conn:
            # Clear index for rebuild
            conn.execute("DELETE FROM license_index")
            conn.execute("DELETE FROM licenses")

            for lic in licenses_data:
                license_id = lic["licenseId"]
                try:
                    # Fetch raw license text for indexing
                    text_url = f"https://raw.githubusercontent.com/spdx/license-list-data/main/text/{license_id}.txt"
                    text_resp = requests.get(text_url)
                    if text_resp.status_code == 200:
                        raw_text = text_resp.text
                        norm_text = normalize_text(raw_text)
                        
                        conn.execute("""
                            INSERT INTO licenses (
                                licenseId, is_spdx, is_osi_approved, is_fsf_libre
                            ) VALUES (?, ?, ?, ?)
                        """, (
                            license_id,
                            True,
                            lic.get("isOsiApproved", False),
                            lic.get("isFsfLibre", False)
                        ))
                        
                        conn.execute("""
                            INSERT INTO license_index (licenseId, search_text)
                            VALUES (?, ?)
                        """, (license_id, norm_text))
                except Exception as e:
                    print(f"Failed to fetch text for {license_id}: {e}")

    def search_candidates(self, text: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Tier 1: Search for candidates using trigram FTS5."""
        norm_text = normalize_text(text)
        # SQLite FTS5 trigram search
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            # FTS5 trigram search works best with a representative snippet or the whole text.
            # Trigram search is very effective for finding similar strings even with minor differences.
            query = """
                SELECT licenseId, search_text
                FROM license_index
                WHERE search_text MATCH ?
                LIMIT ?
            """
            # In FTS5, we can use the text itself as the query.
            # For trigram, it will match shared trigrams.
            try:
                # We use a simplified MATCH query. Real one might need escaping or structured query.
                # Escape double quotes for MATCH
                match_query = norm_text.replace('"', '""')
                cursor = conn.execute(query, (match_query, limit))
                return [dict(row) for row in cursor.fetchall()]
            except sqlite3.OperationalError:
                # Fallback if MATCH fails due to syntax or empty index
                return []

    def get_license_details(self, license_id: str) -> Optional[Dict[str, Any]]:
        """Get full metadata for a license."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM licenses WHERE licenseId = ?", (license_id,)).fetchone()
            return dict(row) if row else None
