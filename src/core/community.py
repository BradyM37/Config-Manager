"""
Community Presets
Fetch and share presets from the community repository
"""

import json
import requests
from pathlib import Path
from typing import Optional
from datetime import datetime

from .backup import get_config_dir

# GitHub raw URLs for community presets
GITHUB_OWNER = "BradyM37"
GITHUB_REPO = "Config-Manager"
GITHUB_BRANCH = "main"
MANIFEST_URL = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}/community-presets/manifest.json"
PRESET_BASE_URL = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}/community-presets"

# Cache settings
CACHE_DURATION_HOURS = 1


def get_community_cache_dir() -> Path:
    """Get cache directory for community presets"""
    cache_dir = get_config_dir() / "community_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_cached_manifest() -> Optional[dict]:
    """Get cached manifest if still valid"""
    cache_file = get_community_cache_dir() / "manifest.json"
    
    if not cache_file.exists():
        return None
    
    try:
        # Check if cache is still valid
        mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
        age_hours = (datetime.now() - mtime).total_seconds() / 3600
        
        if age_hours > CACHE_DURATION_HOURS:
            return None
        
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None


def save_manifest_cache(manifest: dict):
    """Save manifest to cache"""
    cache_file = get_community_cache_dir() / "manifest.json"
    
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
    except Exception as e:
        print(f"Failed to cache manifest: {e}")


def fetch_community_manifest(force_refresh: bool = False) -> Optional[dict]:
    """
    Fetch the community presets manifest from GitHub
    
    Args:
        force_refresh: Bypass cache and fetch fresh
    
    Returns:
        Manifest dict or None if failed
    """
    # Check cache first
    if not force_refresh:
        cached = get_cached_manifest()
        if cached:
            return cached
    
    try:
        response = requests.get(MANIFEST_URL, timeout=10)
        response.raise_for_status()
        
        manifest = response.json()
        save_manifest_cache(manifest)
        
        return manifest
    except Exception as e:
        print(f"Failed to fetch community manifest: {e}")
        
        # Fall back to cache even if expired
        cache_file = get_community_cache_dir() / "manifest.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        return None


def list_community_presets(force_refresh: bool = False) -> list[dict]:
    """
    List all available community presets
    
    Returns:
        List of preset info dicts
    """
    manifest = fetch_community_manifest(force_refresh)
    
    if not manifest:
        return []
    
    return manifest.get("presets", [])


def download_community_preset(preset_id: str) -> Optional[dict]:
    """
    Download a community preset by ID
    
    Args:
        preset_id: The preset's unique ID
    
    Returns:
        Preset data dict or None if failed
    """
    manifest = fetch_community_manifest()
    
    if not manifest:
        return None
    
    # Find the preset
    preset_info = None
    for p in manifest.get("presets", []):
        if p.get("id") == preset_id:
            preset_info = p
            break
    
    if not preset_info:
        print(f"Preset not found: {preset_id}")
        return None
    
    # Download the preset file
    file_url = f"{PRESET_BASE_URL}/{preset_info['file']}"
    
    try:
        response = requests.get(file_url, timeout=10)
        response.raise_for_status()
        
        preset_data = response.json()
        
        # Cache the downloaded preset
        cache_file = get_community_cache_dir() / f"{preset_id}.json"
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(preset_data, f, indent=2)
        
        return preset_data
    except Exception as e:
        print(f"Failed to download preset {preset_id}: {e}")
        return None


def install_community_preset(preset_id: str, deadlock_path: Path) -> bool:
    """
    Download and install a community preset
    
    Args:
        preset_id: The preset's unique ID
        deadlock_path: Path to Deadlock installation
    
    Returns:
        True if successful
    """
    from .config import apply_convars_to_gameinfo
    from .detector import get_gameinfo_path
    from .backup import create_backup
    
    preset_data = download_community_preset(preset_id)
    
    if not preset_data:
        return False
    
    convars = preset_data.get("convars", {})
    
    if not convars:
        print("Preset has no convars")
        return False
    
    # Create backup before applying
    create_backup(deadlock_path, label=f"pre-community-{preset_id}")
    
    # Apply the convars
    gameinfo_path = get_gameinfo_path(deadlock_path)
    return apply_convars_to_gameinfo(gameinfo_path, convars)


def get_installed_community_presets() -> list[str]:
    """Get list of installed community preset IDs"""
    cache_dir = get_community_cache_dir()
    installed = []
    
    for file in cache_dir.glob("*.json"):
        if file.name != "manifest.json":
            installed.append(file.stem)
    
    return installed


def search_community_presets(query: str) -> list[dict]:
    """
    Search community presets by name, author, or tags
    
    Args:
        query: Search query
    
    Returns:
        List of matching presets
    """
    presets = list_community_presets()
    query = query.lower()
    
    results = []
    for preset in presets:
        # Search in name, author, description, and tags
        searchable = " ".join([
            preset.get("name", ""),
            preset.get("author", ""),
            preset.get("description", ""),
            " ".join(preset.get("tags", []))
        ]).lower()
        
        if query in searchable:
            results.append(preset)
    
    return results


# ============================================================================
# PRESET SUBMISSION (creates a GitHub issue for review)
# ============================================================================

SUBMIT_ISSUE_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/issues/new"


def get_submit_url(preset_name: str, author: str, description: str, convars: dict) -> str:
    """
    Generate a URL to submit a preset for review via GitHub issue
    
    This opens a pre-filled GitHub issue that maintainers can review
    """
    import urllib.parse
    
    convars_json = json.dumps(convars, indent=2)
    
    body = f"""## New Community Preset Submission

**Preset Name:** {preset_name}
**Author:** {author}
**Description:** {description}

### ConVars
```json
{convars_json}
```

---
*Submitted via Deadlock Config Manager*
"""
    
    params = {
        "title": f"[Preset Submission] {preset_name}",
        "body": body,
        "labels": "preset-submission"
    }
    
    return f"{SUBMIT_ISSUE_URL}?{urllib.parse.urlencode(params)}"


if __name__ == "__main__":
    # Test community features
    print("Fetching community presets...")
    presets = list_community_presets(force_refresh=True)
    
    for p in presets:
        print(f"  {p['name']} by {p['author']}: {p['description']}")
