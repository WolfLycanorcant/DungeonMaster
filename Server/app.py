from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv
import sys
import os
from datetime import datetime

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from game import RPGGame, Character, Item, GroqEngine

app = Flask(__name__)

# Initialize Groq engine and game
groq_engine = GroqEngine()
game = RPGGame(groq_engine=groq_engine, save_dir="saves")

@app.route('/api/command', methods=['POST'])
def handle_command():
    if not game.current_player:
        return jsonify({"error": "No active game session"}), 400
        
    data = request.json
    if not data or 'command' not in data:
        return jsonify({"error": "No command provided"}), 400
        
    try:
        # Process the command through the game's command system
        result = game.process_input(data['command'])
        return jsonify({"message": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/save_game', methods=['POST'])
def save_game():
    if not game.current_player:
        return jsonify({"error": "No active game to save"}), 400
        
    save_name = request.json.get('save_name', 'autosave')
    result = game.save_game(save_name)
    return jsonify({"message": result})

@app.route('/api/load_game', methods=['POST'])
def load_game():
    save_name = request.json.get('save_name', 'autosave')
    result = game.load_game(save_name)
    return jsonify({"message": result})

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
        # Get equipped items
        equipment = {}
        if hasattr(game.current_player, 'equipped'):
            for slot, item in game.current_player.equipped.items():
                if item:
                    equipment[slot] = {
                        'name': getattr(item, 'name', 'Unknown'),
                        'type': getattr(item, 'item_type', 'item'),
                        'durability': getattr(item, 'durability', 100)
                    }
                else:
                    equipment[slot] = None
        
        return jsonify({
            "name": game.current_player.name,
            "class": game.current_player.character_class,
            "health": game.current_player.hit_points,
            "max_health": game.current_player.calculate_hit_points(),
            "level": game.current_player.level,
            "attributes": game.current_player.attributes,
            "equipment": equipment
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

from flask import Response, stream_with_context
import json

def generate_stream_response(command, game):
    try:
        # Create context for command processing
        context = {
            "player": {
                "name": game.current_player.name if game.current_player else "Unknown",
                "class": game.current_player.character_class if game.current_player else "Unknown",
                "level": game.current_player.level if game.current_player else 0
            },
            "current_location": game.current_player.current_location if game.current_player else "Unknown",
            "combat_mode": game.combat_mode
        }

        # Check for movement commands with various prefixes
        movement_prefixes = [
            'go ', 'walk ', 'travel ', 'move ', 'head ', 'proceed to ', 'enter ', 'goto '
        ]

        # Check if command starts with any movement prefix
        is_movement = any(command.lower().startswith(prefix.lower()) for prefix in movement_prefixes)

        # Process the command once
        response = game.process_input(command, context)
        
        # If it's a movement command, send the response and return
        if is_movement:
            if response:
                yield f"data: {json.dumps({'type': 'response', 'content': response})}\n\n"
            return

        # Special handling for combat
        if command.lower() == "attack" and game.combat_mode and game.current_player:
            # Send initial response if any
            if response:
                yield f"data: {json.dumps({'type': 'response', 'content': response})}\n\n"
                
            # Generate combat description
            player_tuple = (
                game.current_player.name,
                game.current_player.character_class,
                game.current_player.level,
                game.current_player.hit_points
            )
            
            enemy_name = game.current_enemy.get('name', 'Unknown Enemy') if isinstance(game.current_enemy, dict) else getattr(game.current_enemy, 'name', 'Unknown Enemy')
            enemy_level = game.current_enemy.get('level', 'N/A') if isinstance(game.current_enemy, dict) else getattr(game.current_enemy, 'level', 'N/A')
            enemy_hp = game.current_enemy.get('hit_points', 'N/A') if isinstance(game.current_enemy, dict) else getattr(game.current_enemy, 'hit_points', 'N/A')

            enemy_tuple = (enemy_name, enemy_level, enemy_hp)
            
            # Stream combat description
            combat_desc = game.groq_engine.generate_combat_description(player_tuple, enemy_tuple)
            yield f"data: {json.dumps({'type': 'combat_description', 'content': combat_desc})}\n\n"
            
            # Stream combat result
            combat_result = game.handle_attack()
            yield f"data: {json.dumps({'type': 'combat_result', 'content': combat_result})}\n\n"
        # For all other commands, just send the response if it exists
        elif response:
            yield f"data: {json.dumps({'type': 'response', 'content': response})}\n\n"

        # Send final game state update if we have a player
        if game.current_player:
            game_state = {
                'type': 'game_state',
                'content': {
                    'player': {
                        'name': game.current_player.name,
                        'health': game.current_player.hit_points,
                        'level': game.current_player.level,
                        'location': game.current_player.current_location
                    },
                    'combat_mode': game.combat_mode
                }
            }
            yield f"data: {json.dumps(game_state)}\n\n"
            
    except Exception as e:
        app.logger.error("Error in command processing: %s", str(e), exc_info=True)
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
    finally:
        yield "data: {\"type\": \"end\"}\n\n"

@app.route('/api/console_command', methods=['POST'])
def console_command():
    data = request.get_json()
    if not data or 'command' not in data:
        return jsonify({"error": "No command provided"}), 400

    command = data['command'].strip()
    if not command:
        return jsonify({"error": "Empty command"}), 400

    return Response(
        stream_with_context(generate_stream_response(command, game)),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'  # Disable buffering in nginx if used
        }
    )

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
    player_message = data.get('message', '')

    if not npc_name:
        return jsonify({"error": "NPC name is required"}), 400

    if not game.current_player:
        return jsonify({"error": "No player created"}), 400

    location_data = game.get_current_location()
    # Case-insensitive check for NPC presence
    npcs_in_location = [npc.lower() for npc in location_data.get("npcs", [])]
    if npc_name.lower() not in npcs_in_location:
        return jsonify({"error": f"NPC '{npc_name}' not found in {game.current_player.current_location}"}), 400

    try:
        # Check if this is coming from the console command (which might pass relationship_status)
        if 'relationship_status' in data:
            return jsonify({
                "error": "Please use the 'Talk to NPC' button to interact with NPCs"
            }), 400

        # Get the actual NPC name with correct casing
        actual_npc_name = next((npc for npc in location_data.get("npcs", []) 
                              if npc.lower() == npc_name.lower()), npc_name)
        
        # Get NPC object for additional context
        npc = game.npc_memory.get_npc(actual_npc_name)
        npc_role = getattr(npc, 'role', 'person') if npc else 'person'
        
        # Generate dialogue with context
        dialogue = game.groq_engine.generate_npc_dialogue(
            npc_name=actual_npc_name,
            player_name=game.current_player.name,
            player_class=game.current_player.character_class,
            location=game.current_player.current_location,
            player_message=player_message,
            npc_role=npc_role
        )
        
        # Update last interaction time
        if npc:
            npc.last_interaction = datetime.now()
            
        return jsonify({
            "dialogue": dialogue,
            "npc_name": actual_npc_name,
            "npc_role": npc_role
        })
        
    except Exception as e:
        error_msg = str(e)
        app.logger.error("Error in /api/get_npc_dialogue for NPC '%s': %s", npc_name, error_msg, exc_info=True)
        
        # Check for the specific error about relationship_status
        if "unexpected keyword argument 'relationship_status'" in error_msg:
            return jsonify({
                "error": "Please use the 'Talk to NPC' button to interact with NPCs",
                "error_code": "use_npc_button"
            }), 400
            
        return jsonify({"error": f"Failed to generate NPC dialogue: {error_msg}"}), 500

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