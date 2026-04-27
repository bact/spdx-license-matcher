# SPDX-FileCopyrightText: 2026 SPDX
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: Apache-2.0

__version__ = "0.1.0"

from licenseid.matcher import AggregatedLicenseMatcher
from licenseid.database import LicenseDatabase, normalize_text

__all__ = [
    "AggregatedLicenseMatcher",
    "LicenseDatabase",
    "normalize_text",
]
