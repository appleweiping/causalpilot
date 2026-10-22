"""Download Kevin Hillstrom's MineThatData e-mail experiment (64,000 customers).

The data was published in March 2008 for the "MineThatData E-Mail Analytics and
Data Mining Challenge":
https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html

Customers who bought in the last 12 months were split at random into thirds:
Mens e-mail, Womens e-mail, no e-mail. Visits, conversions and spend were tracked
for two weeks. The file is not redistributed here; it is downloaded from the
author's site and checked against a fixed SHA-256.
"""

from __future__ import annotations

import hashlib
import os
import urllib.request
from pathlib import Path

URL = "http://www.minethatdata.com/Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv"
SHA256 = "0e5893329d8b93cefecc571777672028290ab69865718020c78c7284f291aece"
FILENAME = "hillstrom_2008.csv"

# The settings used for examples/hillstrom. `history` is the customer's spend in
# the year before the test, so it is a valid pre-experiment covariate.
ANALYSIS = {
    "group": "segment",
    "control": "No E-Mail",
    "metrics": ["spend", "visit", "conversion"],
    "covariates": ["recency", "history", "mens", "womens", "newbie", "zip_code", "channel"],
    "min_lift": 0.05,
}


def default_cache() -> Path:
    base = os.environ.get("CAUSALPILOT_CACHE") or os.environ.get("XDG_CACHE_HOME")
    return Path(base) / "causalpilot" if base else Path.home() / ".cache" / "causalpilot"


def fetch(cache_dir: str | Path | None = None) -> Path:
    """Return the local path of the dataset, downloading it on first use."""
    folder = Path(cache_dir) if cache_dir else default_cache()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / FILENAME
    if path.exists() and _sha256(path) == SHA256:
        return path
    tmp = path.with_suffix(".part")
    with urllib.request.urlopen(URL, timeout=60) as response, open(tmp, "wb") as handle:
        while chunk := response.read(1 << 16):
            handle.write(chunk)
    digest = _sha256(tmp)
    if digest != SHA256:
        tmp.unlink()
        raise RuntimeError(f"checksum mismatch for {URL}: got {digest}, expected {SHA256}")
    tmp.replace(path)
    return path


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()
