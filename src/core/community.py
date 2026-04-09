"""
Community Presets
Fetch and share presets from Supabase backend
"""

import json
import hashlib
import requests
from pathlib import Path
from typing import Optional
from datetime import datetime
import uuid

from .backup import get_config_dir

# Supabase configuration
SUPABASE_URL = "https://oqsubqktlrvvjsgwjrsz.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9xc3VicWt0bHJ2dmpzZ3dqcnN6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU2NzYzNjMsImV4cCI6MjA5MTI1MjM2M30.1qTzWPaKHWImTAdwhFQJroijxtFwB_XyU-qS78tysMQ"

# Headers for Supabase REST API
def _get_headers():
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }


def get_community_cache_dir() -> Path:
    """Get cache directory for community presets"""
    cache_dir = get_config_dir() / "community_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _get_device_fingerprint() -> str:
    """Generate a semi-unique device fingerprint for vote tracking"""
    import platform
    import getpass
    
    data = f"{platform.node()}-{getpass.getuser()}-{platform.machine()}"
    return hashlib.sha256(data.encode()).hexdigest()[:32]


# ============================================================================
# FETCHING PRESETS
# ============================================================================

def list_community_presets(
    approved_only: bool = True,
    sort_by: str = "downloads",
    limit: int = 50
) -> list[dict]:
    """
    List all available community presets
    
    Args:
        approved_only: Only show approved presets
        sort_by: Sort field (downloads, upvotes, created_at)
        limit: Max results
    
    Returns:
        List of preset info dicts
    """
    try:
        url = f"{SUPABASE_URL}/rest/v1/community_presets"
        params = {
            "select": "id,name,author,description,tags,downloads,upvotes,downvotes,created_at",
            "order": f"{sort_by}.desc",
            "limit": limit
        }
        
        if approved_only:
            params["approved"] = "eq.true"
        
        response = requests.get(url, headers=_get_headers(), params=params, timeout=10)
        response.raise_for_status()
        
        return response.json()
    except Exception as e:
        print(f"Failed to fetch community presets: {e}")
        return []


def get_preset(preset_id: str) -> Optional[dict]:
    """
    Get a single preset by ID (includes convars)
    
    Args:
        preset_id: UUID of the preset
    
    Returns:
        Full preset data or None
    """
    try:
        url = f"{SUPABASE_URL}/rest/v1/community_presets"
        params = {
            "id": f"eq.{preset_id}",
            "select": "*"
        }
        
        response = requests.get(url, headers=_get_headers(), params=params, timeout=10)
        response.raise_for_status()
        
        results = response.json()
        return results[0] if results else None
    except Exception as e:
        print(f"Failed to fetch preset {preset_id}: {e}")
        return None


def download_community_preset(preset_id: str) -> Optional[dict]:
    """
    Download a community preset and increment download counter
    
    Args:
        preset_id: UUID of the preset
    
    Returns:
        Preset data dict or None
    """
    preset = get_preset(preset_id)
    
    if not preset:
        return None
    
    # Increment download counter
    try:
        url = f"{SUPABASE_URL}/rest/v1/rpc/increment_downloads"
        requests.post(
            url,
            headers=_get_headers(),
            json={"preset_uuid": preset_id},
            timeout=5
        )
    except:
        pass  # Don't fail if counter update fails
    
    # Cache locally
    cache_file = get_community_cache_dir() / f"{preset_id}.json"
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(preset, f, indent=2)
    except:
        pass
    
    return preset


def search_community_presets(query: str, limit: int = 20) -> list[dict]:
    """
    Search community presets by name, author, or description
    
    Args:
        query: Search query
        limit: Max results
    
    Returns:
        List of matching presets
    """
    try:
        url = f"{SUPABASE_URL}/rest/v1/community_presets"
        # Use ilike for case-insensitive search
        params = {
            "select": "id,name,author,description,tags,downloads,upvotes,downvotes,created_at",
            "or": f"(name.ilike.*{query}*,author.ilike.*{query}*,description.ilike.*{query}*)",
            "approved": "eq.true",
            "limit": limit
        }
        
        response = requests.get(url, headers=_get_headers(), params=params, timeout=10)
        response.raise_for_status()
        
        return response.json()
    except Exception as e:
        print(f"Failed to search presets: {e}")
        return []


# ============================================================================
# VOTING
# ============================================================================

def vote_preset(preset_id: str, vote_type: int) -> bool:
    """
    Vote on a preset (upvote or downvote)
    
    Args:
        preset_id: UUID of the preset
        vote_type: 1 for upvote, -1 for downvote
    
    Returns:
        True if vote was recorded
    """
    if vote_type not in (-1, 1):
        return False
    
    fingerprint = _get_device_fingerprint()
    
    try:
        url = f"{SUPABASE_URL}/rest/v1/preset_votes"
        
        # Upsert vote (update if exists, insert if not)
        headers = _get_headers()
        headers["Prefer"] = "resolution=merge-duplicates"
        
        response = requests.post(
            url,
            headers=headers,
            json={
                "preset_id": preset_id,
                "fingerprint": fingerprint,
                "vote_type": vote_type
            },
            timeout=10
        )
        response.raise_for_status()
        
        # Update vote counts on preset
        _update_vote_counts(preset_id)
        
        return True
    except Exception as e:
        print(f"Failed to vote: {e}")
        return False


def _update_vote_counts(preset_id: str):
    """Recalculate vote counts for a preset"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/rpc/update_vote_counts"
        requests.post(
            url,
            headers=_get_headers(),
            json={"preset_uuid": preset_id},
            timeout=5
        )
    except:
        pass


def get_user_vote(preset_id: str) -> Optional[int]:
    """
    Get current user's vote on a preset
    
    Returns:
        1, -1, or None if not voted
    """
    fingerprint = _get_device_fingerprint()
    
    try:
        url = f"{SUPABASE_URL}/rest/v1/preset_votes"
        params = {
            "preset_id": f"eq.{preset_id}",
            "fingerprint": f"eq.{fingerprint}",
            "select": "vote_type"
        }
        
        response = requests.get(url, headers=_get_headers(), params=params, timeout=10)
        response.raise_for_status()
        
        results = response.json()
        return results[0]["vote_type"] if results else None
    except:
        return None


# ============================================================================
# SUBMISSIONS
# ============================================================================

def submit_preset(
    name: str,
    author: str,
    description: str,
    convars: dict,
    tags: list[str] = None
) -> Optional[str]:
    """
    Submit a new preset for review
    
    Args:
        name: Preset name
        author: Author name
        description: What this preset does
        convars: Dict of convar settings
        tags: List of tags
    
    Returns:
        Submission ID if successful, None otherwise
    """
    try:
        url = f"{SUPABASE_URL}/rest/v1/preset_submissions"
        
        payload = {
            "name": name,
            "author": author,
            "description": description,
            "convars": convars,
            "tags": tags or []
        }
        
        response = requests.post(
            url,
            headers=_get_headers(),
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        
        result = response.json()
        return result[0]["id"] if result else None
    except Exception as e:
        print(f"Failed to submit preset: {e}")
        return None


def get_submission_status(submission_id: str) -> Optional[dict]:
    """Check status of a submitted preset"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/preset_submissions"
        params = {
            "id": f"eq.{submission_id}",
            "select": "id,name,status,reviewer_notes,submitted_at,reviewed_at"
        }
        
        response = requests.get(url, headers=_get_headers(), params=params, timeout=10)
        response.raise_for_status()
        
        results = response.json()
        return results[0] if results else None
    except:
        return None


# ============================================================================
# INSTALLATION
# ============================================================================

def install_community_preset(preset_id: str, deadlock_path: Path) -> bool:
    """
    Download and install a community preset
    
    Args:
        preset_id: UUID of the preset
        deadlock_path: Path to Deadlock installation
    
    Returns:
        True if successful
    """
    from .config import apply_convars_to_gameinfo, write_video_settings
    from .detector import get_gameinfo_path
    from .backup import create_backup
    
    preset_data = download_community_preset(preset_id)
    
    if not preset_data:
        return False
    
    # Create backup before applying
    create_backup(deadlock_path, label=f"pre-community-{preset_id[:8]}")
    
    preset_type = preset_data.get("type", "json")
    success = True
    
    if preset_type == "both":
        # New format: apply both video.txt and gameinfo.gi settings
        video_settings = preset_data.get("video", {})
        convar_settings = preset_data.get("convars", {})
        
        if video_settings:
            success = write_video_settings(deadlock_path, video_settings, backup=False) and success
        if convar_settings:
            gameinfo_path = get_gameinfo_path(deadlock_path)
            success = apply_convars_to_gameinfo(gameinfo_path, convar_settings) and success
        
        return success
    elif preset_type == "video":
        # Video-only preset
        video_settings = preset_data.get("video", preset_data.get("settings", {}))
        if video_settings:
            return write_video_settings(deadlock_path, video_settings, backup=False)
        return False
    else:
        # Legacy format: auto-detect and route settings to correct files
        convars = preset_data.get("convars", {})
        
        if not convars:
            print("Preset has no convars")
            return False
        
        # Load video settings list from convars.json
        video_setting_names = _get_video_setting_names()
        
        # Split settings by destination
        video_settings = {}
        gameinfo_convars = {}
        
        for name, value in convars.items():
            if name in video_setting_names:
                video_settings[name] = value
            else:
                gameinfo_convars[name] = value
        
        print(f"[Community] Routing {len(video_settings)} to video.txt, {len(gameinfo_convars)} to gameinfo.gi")
        
        success = True
        
        # Apply video settings
        if video_settings:
            result = write_video_settings(deadlock_path, video_settings, backup=False)
            print(f"[Community] video.txt write: {result}")
            success = result and success
        
        # Apply gameinfo convars
        if gameinfo_convars:
            gameinfo_path = get_gameinfo_path(deadlock_path)
            result = apply_convars_to_gameinfo(gameinfo_path, gameinfo_convars)
            print(f"[Community] gameinfo.gi write: {result}")
            success = result and success
        
        return success


def _get_video_setting_names() -> set:
    """Get set of setting names that go to video.txt (source='video' in convars.json)"""
    import json
    from pathlib import Path
    
    video_names = set()
    
    # Also include known video.txt settings not in convars.json
    known_video = {
        'r_shadows', 'r_citadel_shadow_quality', 'csm_max_shadow_dist_override',
        'csm_max_num_cascades_override', 'lb_enable_shadow_casting', 'lb_dynamic_shadow_resolution',
        'r_citadel_ssao', 'r_citadel_ssao_quality', 'r_citadel_distancefield_ao_quality',
        'r_effects_bloom', 'r_post_bloom', 'r_depth_of_field', 'r_citadel_fog_quality',
        'r_particle_max_detail_level', 'r_particle_shadows', 'r_texture_stream_mip_bias',
        'r_dashboard_render_quality', 'r_area_lights', 'r_arealights',
        'gpu_level', 'cpu_level', 'r_citadel_motion_blur', 'r_citadel_antialiasing',
        'r_citadel_outlines', 'r_ssao', 'r_volumetric_fog', 'r_motion_blur_enabled',
        'r_antialias_quality', 'csm_quality_level'
    }
    video_names.update(known_video)
    
    # Try to load from convars.json for dynamic additions
    try:
        json_path = Path(__file__).parent.parent / "data" / "convars.json"
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for category in data.get("categories", []):
                for convar in category.get("convars", []):
                    if convar.get("source") == "video":
                        video_names.add(convar["name"])
    except Exception as e:
        print(f"[Community] Failed to load convars.json: {e}")
    
    return video_names


def get_installed_community_presets() -> list[str]:
    """Get list of installed community preset IDs"""
    cache_dir = get_community_cache_dir()
    installed = []
    
    for file in cache_dir.glob("*.json"):
        if file.name not in ("manifest.json",):
            installed.append(file.stem)
    
    return installed


# ============================================================================
# ADMIN FUNCTIONS
# ============================================================================

# Admin secret key - only you know this
ADMIN_SECRET = "brady_dcm_admin_2026"


def verify_admin(secret: str) -> bool:
    """Verify admin secret key"""
    return secret == ADMIN_SECRET


def list_pending_submissions(secret: str) -> list[dict]:
    """
    List all pending preset submissions awaiting review
    
    Args:
        secret: Admin secret key
    
    Returns:
        List of pending submissions
    """
    if not verify_admin(secret):
        return []
    
    try:
        url = f"{SUPABASE_URL}/rest/v1/preset_submissions"
        params = {
            "status": "eq.pending",
            "select": "*",
            "order": "submitted_at.asc"
        }
        
        response = requests.get(url, headers=_get_headers(), params=params, timeout=10)
        response.raise_for_status()
        
        return response.json()
    except Exception as e:
        print(f"Failed to fetch pending submissions: {e}")
        return []


def approve_submission(secret: str, submission_id: str, reviewer_notes: str = "") -> bool:
    """
    Approve a submission and add it to community_presets
    
    Args:
        secret: Admin secret key
        submission_id: UUID of the submission
        reviewer_notes: Optional notes for the author
    
    Returns:
        True if successful
    """
    if not verify_admin(secret):
        return False
    
    try:
        # Get the submission
        url = f"{SUPABASE_URL}/rest/v1/preset_submissions"
        params = {"id": f"eq.{submission_id}", "select": "*"}
        response = requests.get(url, headers=_get_headers(), params=params, timeout=10)
        response.raise_for_status()
        
        submissions = response.json()
        if not submissions:
            return False
        
        submission = submissions[0]
        
        # Add to community_presets
        preset_url = f"{SUPABASE_URL}/rest/v1/community_presets"
        preset_data = {
            "name": submission["name"],
            "author": submission["author"],
            "description": submission.get("description", ""),
            "convars": submission.get("convars", {}),
            "video": submission.get("video", {}),
            "tags": submission.get("tags", []),
            "type": submission.get("type", "convars"),
            "approved": True,
            "downloads": 0,
            "upvotes": 0,
            "downvotes": 0
        }
        
        response = requests.post(preset_url, headers=_get_headers(), json=preset_data, timeout=10)
        response.raise_for_status()
        
        # Update submission status
        update_url = f"{SUPABASE_URL}/rest/v1/preset_submissions"
        update_params = {"id": f"eq.{submission_id}"}
        update_data = {
            "status": "approved",
            "reviewer_notes": reviewer_notes,
            "reviewed_at": datetime.utcnow().isoformat()
        }
        
        response = requests.patch(
            update_url, 
            headers=_get_headers(), 
            params=update_params,
            json=update_data, 
            timeout=10
        )
        response.raise_for_status()
        
        return True
    except Exception as e:
        print(f"Failed to approve submission: {e}")
        return False


def reject_submission(secret: str, submission_id: str, reviewer_notes: str = "") -> bool:
    """
    Reject a submission
    
    Args:
        secret: Admin secret key
        submission_id: UUID of the submission
        reviewer_notes: Reason for rejection (shown to author)
    
    Returns:
        True if successful
    """
    if not verify_admin(secret):
        return False
    
    try:
        url = f"{SUPABASE_URL}/rest/v1/preset_submissions"
        params = {"id": f"eq.{submission_id}"}
        data = {
            "status": "rejected",
            "reviewer_notes": reviewer_notes,
            "reviewed_at": datetime.utcnow().isoformat()
        }
        
        response = requests.patch(
            url, 
            headers=_get_headers(), 
            params=params,
            json=data, 
            timeout=10
        )
        response.raise_for_status()
        
        return True
    except Exception as e:
        print(f"Failed to reject submission: {e}")
        return False


def delete_community_preset(secret: str, preset_id: str) -> bool:
    """
    Delete a community preset (for removing problematic ones)
    
    Args:
        secret: Admin secret key
        preset_id: UUID of the preset to delete
    
    Returns:
        True if successful
    """
    if not verify_admin(secret):
        return False
    
    try:
        url = f"{SUPABASE_URL}/rest/v1/community_presets"
        params = {"id": f"eq.{preset_id}"}
        
        response = requests.delete(url, headers=_get_headers(), params=params, timeout=10)
        response.raise_for_status()
        
        return True
    except Exception as e:
        print(f"Failed to delete preset: {e}")
        return False


def get_admin_stats(secret: str) -> dict:
    """
    Get admin statistics
    
    Returns:
        Dict with counts and stats
    """
    if not verify_admin(secret):
        return {}
    
    stats = {
        "pending_count": 0,
        "approved_count": 0,
        "rejected_count": 0,
        "total_downloads": 0
    }
    
    try:
        # Count pending
        url = f"{SUPABASE_URL}/rest/v1/preset_submissions"
        params = {"status": "eq.pending", "select": "id"}
        response = requests.get(url, headers=_get_headers(), params=params, timeout=10)
        if response.ok:
            stats["pending_count"] = len(response.json())
        
        # Count approved presets
        url = f"{SUPABASE_URL}/rest/v1/community_presets"
        params = {"select": "id,downloads"}
        response = requests.get(url, headers=_get_headers(), params=params, timeout=10)
        if response.ok:
            presets = response.json()
            stats["approved_count"] = len(presets)
            stats["total_downloads"] = sum(p.get("downloads", 0) for p in presets)
        
        # Count rejected
        url = f"{SUPABASE_URL}/rest/v1/preset_submissions"
        params = {"status": "eq.rejected", "select": "id"}
        response = requests.get(url, headers=_get_headers(), params=params, timeout=10)
        if response.ok:
            stats["rejected_count"] = len(response.json())
        
    except Exception as e:
        print(f"Failed to get admin stats: {e}")
    
    return stats


# ============================================================================
# LEGACY GITHUB SUPPORT (fallback)
# ============================================================================

GITHUB_OWNER = "BradyM37"
GITHUB_REPO = "Config-Manager"
GITHUB_BRANCH = "main"
MANIFEST_URL = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}/community-presets/manifest.json"


def list_github_presets() -> list[dict]:
    """Fallback: fetch presets from GitHub if Supabase is down"""
    try:
        response = requests.get(MANIFEST_URL, timeout=10)
        response.raise_for_status()
        manifest = response.json()
        return manifest.get("presets", [])
    except:
        return []


if __name__ == "__main__":
    # Test community features
    print("Fetching community presets from Supabase...")
    presets = list_community_presets()
    
    if presets:
        for p in presets:
            print(f"  {p['name']} by {p['author']}: {p.get('description', 'No description')}")
    else:
        print("  No presets found (or Supabase not configured)")
    
    print("\nFallback: GitHub presets...")
    github_presets = list_github_presets()
    for p in github_presets:
        print(f"  {p['name']} by {p['author']}")
