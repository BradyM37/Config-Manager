"""
Config Management
Handles reading, writing, and modifying gameinfo.gi files
"""

import json
import re
import shutil
from pathlib import Path
from typing import Optional

from .detector import get_gameinfo_path
from .backup import create_backup, get_config_dir


def get_presets_dir() -> Path:
    """Get the directory containing preset configs"""
    # First check local data directory (for development)
    local_presets = Path(__file__).parent.parent / "data" / "presets"
    if local_presets.exists():
        return local_presets
    
    # Fall back to AppData for installed version
    app_presets = get_config_dir() / "presets"
    app_presets.mkdir(parents=True, exist_ok=True)
    return app_presets


def list_presets() -> list[dict]:
    """
    List all available config presets (JSON format preferred)
    
    Returns:
        List of preset info dicts with 'name', 'path', 'description'
    """
    presets_dir = get_presets_dir()
    presets = []
    
    # Load JSON presets (preferred - these merge into existing config)
    for file in presets_dir.glob("*.json"):
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            presets.append({
                "name": data.get("name", file.stem),
                "path": file,
                "display": data.get("display", file.stem.title()),
                "description": data.get("description", ""),
                "type": "json",
                "convars": data.get("convars", {})
            })
        except Exception as e:
            print(f"Failed to load preset {file}: {e}")
    
    # Also support legacy .gi files (full replacement)
    for file in presets_dir.glob("*.gi"):
        name = file.stem.lower()
        # Skip if we already have a JSON version
        if any(p["name"] == name for p in presets):
            continue
        
        preset_info = {
            "potato": {"display": "🥔 Potato", "description": "Maximum FPS, minimum visuals."},
            "balanced": {"display": "⚖️ Balanced", "description": "Good FPS with decent visuals."},
            "quality": {"display": "💎 Quality", "description": "Better visuals, still optimized."},
            "competitive": {"display": "🎯 Competitive", "description": "Optimized for visibility in ranked."}
        }
        
        info = preset_info.get(name, {"display": name.title(), "description": "Custom preset"})
        
        presets.append({
            "name": name,
            "path": file,
            "display": info["display"],
            "description": info["description"],
            "type": "gi"
        })
    
    return presets


def apply_preset(deadlock_path: Path, preset_path_or_name, backup: bool = True) -> bool:
    """
    Apply a preset config to Deadlock
    
    For JSON presets: merges convars into existing gameinfo.gi (safer)
    For .gi presets: replaces the entire file (legacy)
    
    Args:
        deadlock_path: Path to Deadlock installation
        preset_path_or_name: Path to preset file or preset name
        backup: Whether to create a backup before applying
    
    Returns:
        True if successful, False otherwise
    """
    # Find the preset
    preset = None
    presets = list_presets()
    
    if isinstance(preset_path_or_name, Path):
        preset_path = preset_path_or_name
        preset = next((p for p in presets if p["path"] == preset_path), None)
        
        if not preset:
            # Legacy path-based apply
            if preset_path.suffix == '.json':
                try:
                    with open(preset_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    preset = {"type": "json", "convars": data.get("convars", {}), "path": preset_path}
                except:
                    return False
            elif preset_path.suffix == '.gi':
                preset = {"type": "gi", "path": preset_path}
    else:
        # Name-based lookup
        preset = next((p for p in presets if p["name"] == preset_path_or_name), None)
    
    if not preset:
        print(f"Preset not found: {preset_path_or_name}")
        return False
    
    gameinfo_path = get_gameinfo_path(deadlock_path)
    
    try:
        if backup:
            create_backup(deadlock_path, label="pre-preset")
        
        if preset.get("type") == "json":
            # Smart merge - only modify ConVars section
            return apply_convars_to_gameinfo(gameinfo_path, preset.get("convars", {}))
        else:
            # Legacy full replacement
            if preset["path"].exists():
                shutil.copy2(preset["path"], gameinfo_path)
                return True
            return False
    except Exception as e:
        print(f"Failed to apply preset: {e}")
        return False


def apply_convars_to_gameinfo(gameinfo_path: Path, convars: dict) -> bool:
    """
    Apply convars to an existing gameinfo.gi file by modifying the ConVars section
    
    This is safer than full file replacement as it preserves all other settings
    """
    if not gameinfo_path.exists():
        return False
    
    try:
        with open(gameinfo_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the ConVars section
        convars_match = re.search(r'(ConVars\s*\{)(.*?)(^\s*\})', content, re.MULTILINE | re.DOTALL)
        
        if not convars_match:
            print("ConVars section not found in gameinfo.gi")
            return False
        
        convars_start = convars_match.group(1)
        convars_section = convars_match.group(2)
        convars_end = convars_match.group(3)
        
        # Update each convar in the section
        new_section = convars_section
        
        for name, value in convars.items():
            # Pattern to match the convar line
            pattern = rf'(^\s*{re.escape(name)}\s+)["\']?[^"\'\}}\n]+["\']?'
            
            if re.search(pattern, new_section, re.MULTILINE | re.IGNORECASE):
                # Convar exists, replace it
                new_section = re.sub(
                    pattern,
                    rf'\1"{value}"',
                    new_section,
                    flags=re.MULTILINE | re.IGNORECASE
                )
            else:
                # Convar doesn't exist, add it at the start of the section
                new_section = f'\n{name} "{value}"' + new_section
        
        # Reconstruct the file
        new_content = content[:convars_match.start()] + convars_start + new_section + convars_end + content[convars_match.end():]
        
        with open(gameinfo_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return True
    
    except Exception as e:
        print(f"Failed to apply convars: {e}")
        return False


def read_convars(deadlock_path: Path) -> dict[str, str]:
    """
    Read current convar values from gameinfo.gi
    
    Returns:
        Dict of convar_name -> value
    """
    gameinfo_path = get_gameinfo_path(deadlock_path)
    convars = {}
    
    if not gameinfo_path.exists():
        return convars
    
    try:
        with open(gameinfo_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the ConVars section
        convars_match = re.search(r'ConVars\s*\{(.+?)^\s*\}', content, re.MULTILINE | re.DOTALL)
        
        if convars_match:
            convars_section = convars_match.group(1)
            
            # Parse convar lines: name "value" or name value
            pattern = r'^\s*([a-z_][a-z0-9_]*)\s+["\']?([^"\'}\n]+)["\']?'
            
            for match in re.finditer(pattern, convars_section, re.MULTILINE | re.IGNORECASE):
                name = match.group(1).strip()
                value = match.group(2).strip().strip('"\'')
                
                # Skip comments and section headers
                if not name.startswith('//') and name not in ['rate', 'min', 'max', 'default', 'version']:
                    convars[name] = value
    
    except Exception as e:
        print(f"Failed to read convars: {e}")
    
    return convars


def modify_convar(deadlock_path: Path, convar_name: str, value: str, backup: bool = True) -> bool:
    """
    Modify a single convar in gameinfo.gi
    """
    gameinfo_path = get_gameinfo_path(deadlock_path)
    
    if not gameinfo_path.exists():
        return False
    
    try:
        if backup:
            create_backup(deadlock_path, label="pre-modify")
        
        return apply_convars_to_gameinfo(gameinfo_path, {convar_name: value})
    
    except Exception as e:
        print(f"Failed to modify convar: {e}")
        return False


def modify_convars(deadlock_path: Path, convars: dict[str, str], backup: bool = True) -> bool:
    """
    Modify multiple convars at once
    """
    gameinfo_path = get_gameinfo_path(deadlock_path)
    
    if not gameinfo_path.exists():
        return False
    
    try:
        if backup:
            create_backup(deadlock_path, label="pre-modify")
        
        return apply_convars_to_gameinfo(gameinfo_path, convars)
    
    except Exception as e:
        print(f"Failed to modify convars: {e}")
        return False


if __name__ == "__main__":
    # Test config management
    from .detector import find_deadlock
    
    path = find_deadlock()
    if path:
        print("Available presets:")
        for p in list_presets():
            print(f"  {p['display']}: {p['description']} [{p.get('type', 'gi')}]")
        
        print("\nCurrent convars (sample):")
        convars = read_convars(path)
        for name, value in list(convars.items())[:10]:
            print(f"  {name} = {value}")
