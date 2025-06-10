import os
import json
import time
from typing import Dict, Any, Optional
from pathlib import Path

SAVE_DIR = "saves"

def ensure_save_dir() -> None:
    """Ensure the save directory exists."""
    os.makedirs(SAVE_DIR, exist_ok=True)

def list_saves() -> list:
    """List all available save files."""
    ensure_save_dir()
    saves = []
    for file in os.listdir(SAVE_DIR):
        if file.endswith('.json'):
            filepath = os.path.join(SAVE_DIR, file)
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    timestamp = data.get('timestamp', 0)
                    saves.append({
                        'filename': file,
                        'name': data.get('save_name', file[:-5]),  # Remove .json
                        'timestamp': timestamp,
                        'date': time.ctime(timestamp),
                        'character': data.get('player', {}).get('name', 'Unknown')
                    })
            except (json.JSONDecodeError, IOError):
                continue
    return sorted(saves, key=lambda x: x['timestamp'], reverse=True)

def save_game(game_data: Dict[str, Any], save_name: Optional[str] = None) -> str:
    """
    Save the game data to a file.
    
    Args:
        game_data: The game data to save
        save_name: Optional custom save name. If None, uses timestamp.
    
    Returns:
        str: The filename the game was saved to
    """
    ensure_save_dir()
    
    if save_name is None:
        timestamp = int(time.time())
        save_name = f"save_{timestamp}"
    elif not save_name.endswith('.json'):
        save_name = f"{save_name}.json"
    
    # Ensure unique filename
    base_name = save_name
    counter = 1
    while os.path.exists(os.path.join(SAVE_DIR, save_name)):
        name, ext = os.path.splitext(base_name)
        save_name = f"{name}_{counter}{ext}"
        counter += 1
    
    filepath = os.path.join(SAVE_DIR, save_name)
    
    # Add metadata
    game_data['save_metadata'] = {
        'timestamp': time.time(),
        'version': '1.0',
        'save_name': os.path.splitext(save_name)[0]
    }
    
    try:
        with open(filepath, 'w') as f:
            json.dump(game_data, f, indent=2)
        return f"Game saved successfully as '{save_name}'"
    except IOError as e:
        return f"Error saving game: {str(e)}"

def load_game(filename: str) -> Dict[str, Any]:
    """
    Load game data from a file.
    
    Args:
        filename: The name of the save file to load
    
    Returns:
        Dict containing the loaded game data or None if loading failed
    """
    filepath = os.path.join(SAVE_DIR, filename)
    if not filepath.endswith('.json'):
        filepath += '.json'
    
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        raise IOError(f"Failed to load save file: {str(e)}")

def delete_save(filename: str) -> str:
    """
    Delete a save file.
    
    Args:
        filename: The name of the save file to delete
    
    Returns:
        str: Status message
    """
    filepath = os.path.join(SAVE_DIR, filename)
    if not filepath.endswith('.json'):
        filepath += '.json'
    
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            return f"Deleted save file: {filename}"
        return f"Save file not found: {filename}"
    except IOError as e:
        return f"Error deleting save file: {str(e)}"
