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
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to create character: {str(e)}"}), 500

@app.route('/api/get_player_status', methods=['GET'])
def get_player_status():
    if game.current_player:
        return jsonify({
            "name": game.current_player.name,
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

@app.route('/api/start_combat', methods=['POST'])
def start_combat():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
    except Exception as e:
        return jsonify({"error": "Invalid JSON data"}), 400
    
    if not game.current_player:
        return jsonify({"error": "No player created"}), 400
    
    game.combat_mode = True
    enemy_name = data.get('enemy_name', 'Goblin')
    enemy = game.enemies.get(enemy_name)
    if not enemy:
        return jsonify({"error": "Invalid enemy name"}), 400
    
    game.current_enemy = Character(enemy_name, "enemy")
    game.current_enemy.hit_points = enemy['hit_points']
    game.current_enemy.attributes = enemy['attributes']
    
    return jsonify({"status": "combat_started"})

@app.route('/api/player_attack', methods=['POST'])
def player_attack():
    if not game.combat_mode:
        return jsonify({"error": "Not in combat"}), 400
    
    result = game.handle_attack()
    return jsonify({"result": result})

@app.route('/api/enemy_attack', methods=['POST'])
def enemy_attack():
    if not game.combat_mode:
        return jsonify({"error": "Not in combat"}), 400
    
    # Simple enemy attack logic
    damage = random.randint(1, 4) + game.current_enemy.attributes.get("strength", 0)
    game.current_player.hit_points -= damage
    
    if game.current_player.hit_points <= 0:
        game.end_combat("You have been defeated!")
        return jsonify({"result": "You have been defeated!", "player_dead": True})
    
    return jsonify({"result": f"Enemy hits you for {damage} damage!"})

@app.route('/api/get_location_description', methods=['GET'])
def get_location_description():
    if not game.current_player:
        return jsonify({"error": "No player created"}), 400
    
    location = game.get_current_location()
    if location:
        try:
            response = game.groq_client.generate(
                model=game.groq_model,
                messages=[{"role": "user", "content": f"Describe the {game.current_player.current_location} in a medieval fantasy style"}],
                temperature=0.7,
                max_tokens=100
            )
            return jsonify({"description": response.choices[0].message.content})
        except Exception as e:
            return jsonify({"error": f"Failed to generate description: {str(e)}"}), 500
    return jsonify({"error": "No current location"}), 400

@app.route('/api/get_npc_dialogue', methods=['POST'])
def get_npc_dialogue():
    data = request.json
    npc_name = data.get('npc_name')
    player_name = game.current_player.name if game.current_player else "Unknown"
    
    if not npc_name:
        return jsonify({"error": "NPC name is required"}), 400
    
    if not game.current_player:
        return jsonify({"error": "No player created"}), 400
    
    location = game.get_current_location()
    if npc_name not in location.get("npcs", []):
        return jsonify({"error": f"NPC {npc_name} not found in this location"}), 400
    
    prompt = f"""You are {npc_name}, an NPC in a medieval fantasy world. 
    A player named {player_name} approaches you in {game.current_player.current_location}.
    Respond in character with a short dialogue."""
    
    try:
        response = game.groq_client.generate(
            model=game.groq_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=100
        )
        return jsonify({"dialogue": response.choices[0].message.content})
    except Exception as e:
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
