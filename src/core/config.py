"""
Config Management
Handles reading, writing, and modifying gameinfo.gi files
"""

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
    List all available config presets
    
    Returns:
        List of preset info dicts with 'name', 'path', 'description'
    """
    presets_dir = get_presets_dir()
    presets = []
    
    preset_info = {
        "potato": {
            "display": "🥔 Potato",
            "description": "Maximum FPS, minimum visuals. For low-end PCs."
        },
        "balanced": {
            "display": "⚖️ Balanced", 
            "description": "Recommended. Good FPS with decent visuals."
        },
        "quality": {
            "display": "💎 Quality",
            "description": "Better visuals, still optimized. For high-end PCs."
        },
        "competitive": {
            "display": "🎯 Competitive",
            "description": "Optimized for visibility and performance in ranked."
        }
    }
    
    for file in presets_dir.glob("*.gi"):
        name = file.stem.lower()
        info = preset_info.get(name, {
            "display": name.title(),
            "description": "Custom preset"
        })
        
        presets.append({
            "name": name,
            "path": file,
            "display": info["display"],
            "description": info["description"]
        })
    
    return presets


def apply_preset(deadlock_path: Path, preset_path: Path, backup: bool = True) -> bool:
    """
    Apply a preset config to Deadlock
    
    Args:
        deadlock_path: Path to Deadlock installation
        preset_path: Path to the preset .gi file
        backup: Whether to create a backup before applying
    
    Returns:
        True if successful, False otherwise
    """
    if not preset_path.exists():
        return False
    
    gameinfo_path = get_gameinfo_path(deadlock_path)
    
    try:
        if backup:
            create_backup(deadlock_path, label="pre-preset")
        
        shutil.copy2(preset_path, gameinfo_path)
        return True
    except Exception as e:
        print(f"Failed to apply preset: {e}")
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
    
    Args:
        deadlock_path: Path to Deadlock installation
        convar_name: Name of the convar to modify
        value: New value
        backup: Whether to create a backup before modifying
    
    Returns:
        True if successful, False otherwise
    """
    gameinfo_path = get_gameinfo_path(deadlock_path)
    
    if not gameinfo_path.exists():
        return False
    
    try:
        with open(gameinfo_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Pattern to match the convar line
        pattern = rf'(^\s*{re.escape(convar_name)}\s+)["\']?[^"\'}\n]+["\']?'
        
        if re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
            # Convar exists, replace it
            new_content = re.sub(
                pattern,
                rf'\1"{value}"',
                content,
                flags=re.MULTILINE | re.IGNORECASE
            )
        else:
            # Convar doesn't exist, we'd need to add it
            # For now, just return False - adding convars is more complex
            return False
        
        if backup:
            create_backup(deadlock_path, label="pre-modify")
        
        with open(gameinfo_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return True
    
    except Exception as e:
        print(f"Failed to modify convar: {e}")
        return False


def modify_convars(deadlock_path: Path, convars: dict[str, str], backup: bool = True) -> bool:
    """
    Modify multiple convars at once
    
    Args:
        deadlock_path: Path to Deadlock installation
        convars: Dict of convar_name -> new_value
        backup: Whether to create a backup before modifying
    
    Returns:
        True if successful, False otherwise
    """
    if backup:
        create_backup(deadlock_path, label="pre-modify")
    
    success = True
    for name, value in convars.items():
        if not modify_convar(deadlock_path, name, value, backup=False):
            success = False
    
    return success


if __name__ == "__main__":
    # Test config management
    from .detector import find_deadlock
    
    path = find_deadlock()
    if path:
        print("Available presets:")
        for p in list_presets():
            print(f"  {p['display']}: {p['description']}")
        
        print("\nCurrent convars (sample):")
        convars = read_convars(path)
        for name, value in list(convars.items())[:10]:
            print(f"  {name} = {value}")
