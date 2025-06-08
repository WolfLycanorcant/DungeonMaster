from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv
import sys
import os

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from game import RPGGame, Character, Item

app = Flask(__name__)
game = RPGGame()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/init_game', methods=['POST'])
def init_game():
    game.initialize_game_data()
    return jsonify({"status": "success"})

@app.route('/api/create_character', methods=['POST'])
def create_character():
    data = request.json
    name = data.get('name')
    character_class = data.get('class')

    if not name or not character_class:
        return jsonify({"error": "Name and class are required"}), 400

    try:
        game.current_player = game.create_character(name, character_class)
        return jsonify({"status": "success", "character": {
            "name": game.current_player.name,
            "class": game.current_player.character_class,
            "level": game.current_player.level,
            "hit_points": game.current_player.hit_points,
            "attributes": game.current_player.attributes
        }})
    except ValueError as e:
        app.logger.error("ValueError in /api/create_character: %s", str(e))
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        app.logger.error("Exception in /api/create_character: %s", str(e), exc_info=True)
        return jsonify({"error": f"Failed to create character: {str(e)}"}), 500

@app.route('/api/get_player_status', methods=['GET'])
def get_player_status():
    if game.current_player:
        return jsonify({
            "name": game.current_player.name,
            "class": game.current_player.character_class,
            "health": game.current_player.hit_points,
            "level": game.current_player.level,
            "attributes": game.current_player.attributes
        })
    return jsonify({"error": "No player created"}), 400

@app.route('/api/get_enemy_status', methods=['GET'])
def get_enemy_status():
    if game.current_enemy:
        return jsonify({
            "name": game.current_enemy.name,
            "health": game.current_enemy.hit_points
        })
    return jsonify({"error": "No enemy in combat"}), 400

@app.route('/api/console_command', methods=['POST'])
def console_command():
    try:
        data = request.get_json()
        if not data or 'command' not in data:
            return jsonify({"error": "No command provided"}), 400

        command = data['command'].lower()

        # Process command using RPGGame's process_input method
        response = game.process_input(
            command,
            {
                "player": {
                    "name": game.current_player.name if game.current_player else "Unknown",
                    "class": game.current_player.character_class if game.current_player else "Unknown",
                    "level": game.current_player.level if game.current_player else 0
                },
                "current_location": game.current_player.current_location if game.current_player else "Unknown",
                "combat_mode": game.combat_mode
            }
        )

        # Process game state changes based on command
        if command.startswith("go "):
            destination = command[3:].strip()
            game_response = game.move_player(destination)
            # This check might be problematic if game_response can be a non-error string that shouldn't just be appended
            # if "error" not in game_response:
            # For now, assuming game_response is either an error string or a success string from move_player
            response = game_response # game.move_player now returns the full descriptive string
        elif command.startswith("talk to"):
            # This part is handled by process_input calling game.groq_engine.generate_npc_dialogue
            # The 'response' from process_input will already contain the dialogue.
            pass # No additional action needed here as process_input handles it.
        elif command == "attack" and game.combat_mode:
            # Create hashable tuples for the new cached generate_combat_description method
            player_tuple = (
                game.current_player.name,
                game.current_player.character_class,
                game.current_player.level,
                game.current_player.hit_points # Current HP
            )
            # Assuming current_enemy has 'name', 'level', 'hit_points' attributes
            # If current_enemy structure is different, this needs adjustment.
            # Based on game.py's enemies dict, 'level' and 'hit_points' are top-level after selecting an enemy.
            # Let's assume game.current_enemy is an object with these attributes, similar to Character.
            # If game.current_enemy is just a dict from self.enemies, then access would be game.current_enemy['name'], etc.
            # Given the previous attempt to pass a dict, game.current_enemy is likely an object or a populated dict.
            # For consistency with player_tuple and GroqEngine method, let's assume it has these attributes.
            # If game.current_enemy might not have a 'level' (e.g. if it's a unique creature not from a template),
            # provide a default.
            # Assuming game.current_enemy is a dictionary taken from game.enemies
            # The 'name' is often the key used to fetch the enemy dict, so it might not be in the dict itself.
            # This needs clarification on how current_enemy is structured/named.
            # For now, let's assume current_enemy dict has a 'name_in_dict' field or we use a placeholder.
            # However, game.handle_attack() uses self.current_enemy.name, suggesting it should be available.
            # Let's assume self.current_enemy = {"name": "Goblin", "level": 1, "hit_points": 10, ...}

            enemy_name = game.current_enemy.get('name', 'Unknown Enemy') if isinstance(game.current_enemy, dict) else getattr(game.current_enemy, 'name', 'Unknown Enemy')
            enemy_level = game.current_enemy.get('level', 'N/A') if isinstance(game.current_enemy, dict) else getattr(game.current_enemy, 'level', 'N/A')
            enemy_hp = game.current_enemy.get('hit_points', 'N/A') if isinstance(game.current_enemy, dict) else getattr(game.current_enemy, 'hit_points', 'N/A')

            enemy_tuple = (
                enemy_name, # Name of the specific enemy instance
                enemy_level,
                enemy_hp
            )

            combat_desc = game.groq_engine.generate_combat_description(player_tuple, enemy_tuple)
            combat_result = game.handle_attack() # This likely modifies HP
            response = f"{combat_desc}\n\n{combat_result}"

        return jsonify({
            "response": response,
            "game_state": {
                "player": {
                    "name": game.current_player.name if game.current_player else None,
                    "health": game.current_player.hit_points if game.current_player else None,
                    "level": game.current_player.level if game.current_player else None
                }
            }
        })

    except Exception as e:
        app.logger.error("Error in /api/console_command: %s", str(e), exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/look_around', methods=['POST'])
def look_around():
    try:
        if not game.current_player:
            return jsonify({"error": "No player created"}), 400

        location_data = game.get_current_location()
        if not location_data:
            return jsonify({"error": "Could not retrieve current location details"}), 400

        description = location_data.get("dynamic_description", "No description available for this location.")

        return jsonify({"description": description})

    except Exception as e:
        app.logger.error("Error in /api/look_around: %s", str(e), exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/check_inventory', methods=['GET'])
def check_inventory():
    if not game.current_player:
        return jsonify({"error": "No player created"}), 400

    inventory = []
    for item in game.current_player.inventory:
        inventory.append({
            "name": item.name,
            "type": item.item_type,
            "stats": item.stats
        })

    return jsonify({
        "inventory": inventory
    })

@app.route('/api/get_location_description', methods=['GET'])
def get_location_description():
    if not game.current_player:
        return jsonify({"error": "No player created"}), 400

    location_data = game.get_current_location()
    if not location_data:
        return jsonify({"error": "Could not retrieve current location details"}), 400

    description = location_data.get("dynamic_description", "No description available for this location.")

    return jsonify({"description": description})

@app.route('/api/get_npc_dialogue', methods=['POST'])
def get_npc_dialogue():
    data = request.json
    npc_name = data.get('npc_name')

    if not npc_name:
        return jsonify({"error": "NPC name is required"}), 400

    if not game.current_player:
        return jsonify({"error": "No player created"}), 400

    location_data = game.get_current_location()
    # Case-insensitive check for NPC presence
    if npc_name.lower() not in [npc.lower() for npc in location_data.get("npcs", [])]:
        return jsonify({"error": f"NPC '{npc_name}' not found in {game.current_player.current_location}"}), 400

    try:
        dialogue = game.groq_engine.generate_npc_dialogue(
            npc_name,
            game.current_player.name,
            game.current_player.current_location
        )
        return jsonify({"dialogue": dialogue})
    except Exception as e:
        app.logger.error("Error in /api/get_npc_dialogue for NPC '%s': %s", npc_name, str(e), exc_info=True)
        return jsonify({"error": f"Failed to generate NPC dialogue: {str(e)}"}), 500

@app.route('/api/move_player', methods=['POST'])
def move_player():
    data = request.json
    destination = data.get('destination')

    if not destination:
        return jsonify({"error": "Destination required"}), 400

    result = game.move_player(destination)
    return jsonify({"result": result})

@app.route('/api/get_inventory', methods=['GET'])
def get_inventory():
    if not game.current_player:
        return jsonify({"error": "No player created"}), 400

    inventory = game.show_inventory()
    return jsonify({"inventory": inventory})

@app.route('/api/equip_item', methods=['POST'])
def equip_item():
    data = request.json
    item_name = data.get('item_name')

    if not item_name:
        return jsonify({"error": "Item name required"}), 400

    result = game.equip_item(item_name)
    return jsonify({"result": result})

@app.route('/api/unequip_item', methods=['POST'])
def unequip_item():
    data = request.json
    slot = data.get('slot')

    if not slot:
        return jsonify({"error": "Slot required"}), 400

    result = game.unequip_item(slot)
    return jsonify({"result": result})

if __name__ == '__main__':
    app.run(port=30000, debug=True)
