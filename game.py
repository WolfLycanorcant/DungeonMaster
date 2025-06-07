import json
import os
import random
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from groq import Groq

class GroqEngine:
    def __init__(self):
        """Initialize the Groq AI engine."""
        load_dotenv()
        self.api_key = os.getenv('GROQ_API_KEY')
        self.model = os.getenv('GROQ_MODEL', 'llama3-8b-8192')
        self.client = None
        self.initialize()

    def initialize(self):
        """Initialize the Groq client."""
        if not self.api_key:
            print("Warning: GROQ_API_KEY not found in .env file. Some features may be limited.")
            return

        try:
            self.client = Groq(api_key=self.api_key)
            print("Groq client initialized successfully")
            
            # Test the connection with a simple request
            test_response = self.client.generate(
                model=self.model,
                messages=[{"role": "user", "content": "Test connection"}],
                max_tokens=10
            )
            print(f"Groq model {self.model} is accessible")
        except Exception as e:
            print(f"Warning: Failed to initialize Groq client: {e}")
            print(f"Make sure your API key has access to model: {self.model}")

    def generate_description(self, context: Dict[str, Any]) -> str:
        """Generate a location description using Groq AI."""
        if not self.client:
            return "The location is dark and foreboding."

        try:
            # Create a structured prompt for location description
            prompt = f"""
            You are a master Dungeon Master. Describe this location:
            {json.dumps(context, indent=2)}
            
            Include:
            - Sensory details (sights, sounds, smells)
            - Environmental conditions
            - Points of interest
            - NPC interactions
            - Potential dangers
            - Interactive elements

            Keep it immersive and engaging.
            """

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a master Dungeon Master. Provide vivid, immersive descriptions of locations and interactions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            # Validate the response
            if not response or not hasattr(response, 'choices') or not response.choices:
                print("Warning: Invalid response from Groq")
                return "The location is dark and foreboding."
                
            return response.choices[0].message.content
        except Exception as e:
            print(f"Warning: Failed to generate description: {e}")
            return "The location is dark and foreboding."

    def generate_npc_dialogue(self, npc_name: str, player_name: str, location: str) -> str:
        """Generate NPC dialogue using Groq AI."""
        if not self.client:
            return f"Hello, {player_name}. Welcome to {location}."

        try:
            # Create a structured prompt for NPC dialogue
            prompt = f"""
            You are {npc_name}, an NPC in a medieval fantasy world.
            A player named {player_name} approaches you in {location}.
            
            Respond in character with:
            - Your personality and backstory
            - Local knowledge
            - Potential quests
            - Interesting dialogue
            
            Keep it immersive and engaging.
            """

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an NPC in a medieval fantasy world. Speak in character and provide engaging dialogue."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            # Validate the response
            if not response or not hasattr(response, 'choices') or not response.choices:
                print("Warning: Invalid response from Groq")
                return f"Hello, {player_name}. Welcome to {location}."
                
            return response.choices[0].message.content
        except Exception as e:
            print(f"Warning: Failed to generate NPC dialogue: {e}")
            return f"Hello, {player_name}. Welcome to {location}."

    def generate_action_description(self, player: Dict[str, Any], action: str) -> str:
        """Generate a description of the player's action using Groq AI."""
        if not self.client:
            return f"{action}"

        try:
            # Create a structured prompt for action description
            prompt = f"""
            You are a master Dungeon Master. Describe this player action:
            Player: {json.dumps(player, indent=2)}
            Action: {action}
            
            Include:
            - Action details
            - Environmental effects
            - Dynamic descriptions
            - Potential outcomes

            Keep it immersive and engaging.
            """

            response = self.client.generate(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2000
            )
            
            # Validate the response
            if not response or not hasattr(response, 'choices') or not response.choices:
                print("Warning: Invalid response from Groq")
                return f"{action}"
                
            return response.choices[0].message.content
        except Exception as e:
            print(f"Warning: Failed to generate action description: {e}")
            return f"{action}"

class Item:
    def __init__(self, name: str, item_type: str, stats: Dict[str, Any], stackable: bool = False, max_stack: int = 1):
        self.name = name
        self.item_type = item_type
        self.stats = stats
        self.stackable = stackable
        self.max_stack = max_stack
        self.quantity = 1 if not stackable else None
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.item_type,
            "stats": self.stats,
            "stackable": self.stackable,
            "max_stack": self.max_stack,
            "quantity": self.quantity
        }

    def __str__(self):
        if self.stackable:
            return f"{self.name} x{self.quantity} ({self.item_type})"
        return f"{self.name} ({self.item_type})"

    def __eq__(self, other):
        if isinstance(other, Item):
            return (self.name == other.name and 
                    self.item_type == other.item_type and 
                    self.stats == other.stats)
        return False

    def can_stack_with(self, other: 'Item') -> bool:
        return (self.stackable and 
                other.stackable and 
                self.name == other.name and 
                self.item_type == other.item_type and 
                self.stats == other.stats)

class Character:
    def __init__(self, name: str, character_class: str, level: int = 1):
        self.name = name
        # Normalize and validate character class
        valid_classes = ['Warrior', 'Mage', 'Rogue']
        character_class = character_class.capitalize()
        if character_class not in valid_classes:
            raise ValueError(f"Invalid character class: {character_class}. Must be one of {', '.join(valid_classes)}")
        self.character_class = character_class
        self.level = level
        self.attributes = {
            "strength": 10,
            "dexterity": 10,
            "constitution": 10,
            "intelligence": 10,
            "wisdom": 10,
            "charisma": 10
        }
        self.hit_points = self.calculate_hit_points()
        self.inventory: List[Item] = []
        self.inventory_weight = 0
        self.max_inventory_weight = 50  # Base weight capacity
        self.equipped = {
            "weapon": None,
            "armor": None,
            "accessories": []
        }
        self.current_location = "Starting Town"

    def unequip_item(self, slot: str) -> str:
        """Unequip an item and return it to inventory"""
        if slot not in self.equipped:
            return f"Invalid equipment slot: {slot}"
            
        item = self.equipped[slot]
        if item:
            self.equipped[slot] = None
            self.inventory.append(item)
            return f"Unequipped {item.name}"
        return "No item equipped in that slot"
        
    def calculate_hit_points(self) -> int:
        base_hp = 10
        con_mod = (self.attributes["constitution"] - 10) // 2
        return base_hp + (con_mod * self.level)
        
    def add_item(self, item: Item):
        self.inventory.append(item)
        
    def equip_item(self, item: Item):
        if item not in self.inventory:
            return f"{item.name} is not in inventory"

        if item.item_type == "weapon":
            self.equipped["weapon"] = item
        elif item.item_type == "armor":
            self.equipped["armor"] = item
        elif item.item_type == "accessory":
            self.equipped["accessories"].append(item)
        else:
            return f"Unknown item type: {item.item_type}"
            
        self.inventory.remove(item)
        return f"Equipped {item.name}"
        
    def get_attack_bonus(self) -> int:
        weapon = self.equipped["weapon"]
        if weapon:
            return self.attributes["strength"] + weapon.stats.get("bonus", 0)
        return self.attributes["strength"]
        
    def get_defense_bonus(self) -> int:
        armor = self.equipped["armor"]
        if armor:
            return self.attributes["dexterity"] + armor.stats.get("bonus", 0)
        return self.attributes["dexterity"]
        
    def get_item(self, item_name: str) -> Optional[Item]:
        for item in self.inventory:
            if item.name.lower() == item_name.lower():
                return item
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "class": self.character_class,
            "level": self.level,
            "attributes": self.attributes,
            "hit_points": self.hit_points,
            "inventory": [item.to_dict() for item in self.inventory],
            "equipped": {
                "weapon": self.equipped["weapon"].to_dict() if self.equipped["weapon"] else None,
                "armor": self.equipped["armor"].to_dict() if self.equipped["armor"] else None,
                "accessories": [item.to_dict() for item in self.equipped["accessories"]]
            }
        }



    def show_inventory(self):
        if not self.current_player:
            return "No player character selected"

        output = [
            "=" * 50,
            "Inventory:",
            "=" * 50,
            f"\nWeight: {self.current_player.inventory_weight}/{self.current_player.max_inventory_weight} kg",
            "-" * 50,
            "\nEquipped:",
            "-" * 10,
            f"Weapon: {self.current_player.equipped['weapon'] or 'None'}",
            f"Armor: {self.current_player.equipped['armor'] or 'None'}"
        ]

        if self.current_player.equipped["accessories"]:
            output.append("\nAccessories:")
            for acc in self.current_player.equipped["accessories"]:
                output.append(f"- {acc}")
        else:
            output.append("\nAccessories: None")

        output.append("\nInventory Items:")
        for item in self.current_player.inventory:
            output.append(f"- {item}")

        return "\n".join(output)

    def equip_item(self, item_name: str) -> str:
        """Equip an item from inventory"""
        if not self.current_player:
            return "No player character selected"

        item = self.current_player.get_item(item_name)
        if not item:
            return f"Item '{item_name}' not found in inventory"

        return self.current_player.equip_item(item)

    def unequip_item(self, slot: str) -> str:
        """Unequip an item from a slot"""
        if not self.current_player:
            return "No player character selected"

        return self.current_player.unequip_item(slot)

    def examine_item(self, item_name: str) -> str:
        """Examine an item in inventory"""
        if not self.current_player:
            return "No player character selected"

        item = self.current_player.get_item(item_name)
        if not item:
            return f"Item '{item_name}' not found in inventory"

        return f"""Examining {item.name}:
Type: {item.item_type}
Stats: {json.dumps(item.stats, indent=2)}
Stackable: {item.stackable}
Max Stack: {item.max_stack}
Quantity: {item.quantity if item.stackable else '1'}"""

    def move_player(self, destination: str) -> str:
        """Move player to a new location"""
        if not self.current_player:
            return "No player character selected"

        if destination not in self.locations:
            return f"Location '{destination}' does not exist"

        self.current_player.current_location = destination
        return f"You have arrived at {destination}.\n{self.locations[destination]['description']}"

    def get_current_location(self) -> Dict[str, Any]:
        """Get current location data"""
        if not self.current_player:
            return None

        location = self.locations.get(self.current_player.current_location)
        if not location:
            return None

        return {
            "name": self.current_player.current_location,
            "description": location["description"],
            "exits": location["exits"],
            "npcs": location["npcs"]
        }

    def start_combat(self, enemy_name: str) -> str:
        """Start combat with an enemy"""
        if not self.current_player:
            return "No player character selected"

        enemy = self.enemies.get(enemy_name)
        if not enemy:
            return f"Enemy '{enemy_name}' does not exist"

        self.current_enemy = Character(
            name=enemy_name,
            character_class="enemy",
            level=enemy["level"]
        )
        self.current_enemy.hit_points = enemy["hit_points"]
        self.current_enemy.attributes = enemy["attributes"]
        self.combat_mode = True

        return f"Combat started with {enemy_name}!"

    def end_combat(self, message: str = "") -> str:
        """End combat mode"""
        self.current_enemy = None
        self.combat_mode = False
        return message

    def handle_attack(self) -> str:
        """Handle player attack in combat"""
        if not self.current_player or not self.current_enemy:
            return "No combat in progress"

        player_attack = self.current_player.get_attack_bonus()
        enemy_defense = self.current_enemy.get_defense_bonus()

        # Simple combat calculation
        hit = random.randint(1, 20) + player_attack - enemy_defense
        if hit > 0:
            damage = random.randint(1, 6) + player_attack
            self.current_enemy.hit_points -= damage
            if self.current_enemy.hit_points <= 0:
                self.end_combat()
                return f"You hit for {damage} damage! {self.current_enemy.name} has been defeated!"
            return f"You hit for {damage} damage! {self.current_enemy.name} has {self.current_enemy.hit_points} HP left."
        return "You missed!"

    def get_player_status(self) -> Dict[str, Any]:
        """Get player status for display"""
        if not self.current_player:
            return None

        return {
            "name": self.current_player.name,
            "class": self.current_player.character_class,
            "level": self.current_player.level,
            "hit_points": self.current_player.hit_points,
            "attributes": self.current_player.attributes
        }

    def get_enemy_status(self) -> Dict[str, Any]:
        """Get enemy status for display"""
        if not self.current_enemy:
            return None

        return {
            "name": self.current_enemy.name,
            "hit_points": self.current_enemy.hit_points
        }

class RPGGame:
    def __init__(self):
        """Initialize the RPG game with default settings."""
        self.current_player = None
        self.current_enemy = None
        self.combat_mode = False
        self.groq_engine = GroqEngine()
        self.rules = {}
        self.session_history = []
        self.current_weather = None
        self.current_time = "morning"
        
        # Initialize session memory
        self.session_memory = {
            "actions": [],
            "last_summary": "",
            "context": {
                "player": {},
                "location": {},
                "environment": {}
            }
        }
        
        self.initialize_game_data()
        self.load_rules()
        
        # Initialize Groq if available
        if self.groq_engine.client:
            print("Groq AI initialized successfully")
        else:
            print("Warning: Groq AI not available. Some features may be limited.")

    def load_rules(self):
        """Load all rule files from the Json Files directory."""
        rules_dir = "Json Files"
        for filename in os.listdir(rules_dir):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(rules_dir, filename), 'r') as f:
                        self.rules[filename] = json.load(f)
                except Exception as e:
                    print(f"Warning: Failed to load {filename}: {e}")

    def update_session_memory(self, action: str, response: str):
        """Update the session memory with the latest action and response."""
        # Update session_history and session_memory with the same data
        self.session_history.append({
            "action": action,
            "response": response,
            "time": self.current_time,
            "location": self.current_player.current_location if self.current_player else "Unknown"
        })
        
        self.session_memory["actions"] = self.session_history[-5:]  # Keep last 5 actions
        self.session_memory["last_summary"] = self._generate_session_summary()

    def _generate_session_summary(self):
        """Generate a summary of recent actions for session context."""
        recent_actions = self.session_memory["actions"][-5:]
        summary = []
        
        for action in recent_actions:
            summary.append(f"[{action['time']}] In {action['location']}: {action['action']}")
            summary.append(f"Response: {action['response'].split('.')[0]}.")
            
        return "\n".join(summary)

    def build_prompt(self, user_input: str) -> str:
        """Build a comprehensive prompt for Groq AI."""
        # Get relevant rules
        relevant_rules = []
        for rule_file, rule_data in self.rules.items():
            if rule_file == "rules.json":  # Always include main rules
                relevant_rules.append(rule_data)
            elif rule_file == "squad_tactics.json" and self.current_player:
                relevant_rules.append(rule_data)
            
        # Build context
        context = {
            "player": {
                "name": self.current_player.name if self.current_player else "Unknown",
                "class": self.current_player.character_class if self.current_player else "Unknown",
                "level": self.current_player.level if self.current_player else 0,
                "inventory": [item.name for item in self.current_player.inventory] if self.current_player else []
            },
            "location": self.current_player.current_location if self.current_player else "Unknown",
            "weather": self.current_weather,
            "time": self.current_time,
            "session_summary": self.session_memory["last_summary"]
        }

        # Build prompt
        prompt = f"""
        You are an expert Dungeon Master AI. Generate a vivid, sensory-rich description of the scene.
        
        [Rules]
        {json.dumps(relevant_rules, indent=2)}
        
        [Current Context]
        {json.dumps(context, indent=2)}
        
        Player input: {user_input}
        
        Please respond with a detailed description that:
        1. Follows the game rules
        2. Maintains consistency with previous actions
        3. Includes sensory details
        4. Provides clear next steps
        """
        
        return prompt

    def process_input(self, user_input: str, context: Dict[str, Any] = None) -> str:
        """Process user input and return a response."""
        if not context:
            context = {}
            
        if not user_input:
            return "Please enter a command."
            
        command = user_input.lower().strip()
        
        # Build prompt
        prompt = self.build_prompt(user_input)
        
        try:
            # Generate response
            response = self.groq_engine.generate_description({
                "prompt": prompt,
                "rules": self.rules,
                "context": context
            })
            
            # Update session memory
            self.update_session_memory(user_input, response)
            
            return response
            
        except Exception as e:
            print(f"Error generating response: {e}")
            return "I'm having trouble generating a response. Please try again."

    def initialize_game_data(self):
        """Initialize game data including locations and items."""
        self.locations = {
            "Starting Town": {
                "description": "A bustling town with cobblestone streets and wooden houses.",
                "exits": ["Forest", "Market Square"],
                "npcs": ["Mayor", "Shopkeeper", "Guard"]
            },
            "Forest": {
                "description": "A dense forest with tall trees and winding paths.",
                "exits": ["Starting Town", "Cave"],
                "enemies": ["Goblin", "Wolf", "Bandit"],
                "npcs": ["Forest Ranger", "Herbalist"]
            },
            "Market Square": {
                "description": "A busy marketplace with various shops and stalls.",
                "exits": ["Starting Town", "Blacksmith", "Tavern"],
                "npcs": ["Merchant", "Blacksmith", "Innkeeper"]
            },
            "Cave": {
                "description": "A dark and foreboding cave with glowing crystals.",
                "exits": ["Forest"],
                "enemies": ["Goblin", "Orc Warrior", "Cave Spider"]
            }
        }

        self.enemies = {
            "Goblin": {
                "level": 1,
                "hit_points": 10,
                "attributes": {
                    "strength": 8,
                    "dexterity": 12,
                    "constitution": 9
                }
            },
            "Orc Warrior": {
                "level": 2,
                "hit_points": 15,
                "attributes": {
                    "strength": 14,
                    "dexterity": 10,
                    "constitution": 12
                }
            },
            "Wolf": {
                "level": 1,
                "hit_points": 8,
                "attributes": {
                    "strength": 10,
                    "dexterity": 15,
                    "constitution": 8
                }
            },
            "Bandit": {
                "level": 2,
                "hit_points": 12,
                "attributes": {
                    "strength": 12,
                    "dexterity": 14,
                    "constitution": 10
                }
            },
            "Cave Spider": {
                "level": 3,
                "hit_points": 20,
                "attributes": {
                    "strength": 15,
                    "dexterity": 18,
                    "constitution": 12
                }
            }
        }

    def create_character(self, name: str, character_class: str) -> Character:
        """Create a new character with the given name and class."""
        try:
            self.current_player = Character(name, character_class)
            # Add starting items based on class
            if character_class.lower() == "warrior":
                self.current_player.add_item(Item("Iron Sword", "weapon", {"bonus": 5, "weight": 2}))
                self.current_player.add_item(Item("Leather Armor", "armor", {"bonus": 3, "weight": 3}))
            elif character_class.lower() == "mage":
                self.current_player.add_item(Item("Wooden Staff", "weapon", {"bonus": 3, "weight": 1}))
                self.current_player.add_item(Item("Robe", "armor", {"bonus": 1, "weight": 2}))
            elif character_class.lower() == "rogue":
                self.current_player.add_item(Item("Dagger", "weapon", {"bonus": 4, "weight": 1}))
                self.current_player.add_item(Item("Leather Armor", "armor", {"bonus": 2, "weight": 2}))
            return self.current_player
        except ValueError as e:
            print(f"Error creating character: {e}")
            return None

    def get_current_location(self) -> Dict[str, Any]:
        """Get the current location details with Groq-generated description."""
        if not self.current_player:
            return {}
        
        location = self.locations.get(self.current_player.current_location, {})
        if location:
            # Generate dynamic description using Groq
            context = {
                "name": self.current_player.current_location,
                "description": location.get("description", ""),
                "npcs": location.get("npcs", []),
                "enemies": location.get("enemies", []),
                "exits": location.get("exits", [])
            }
            location["dynamic_description"] = self.groq_engine.generate_description(context)
        return location

    def move_player(self, destination: str) -> str:
        """Move the player to a new location if it's a valid destination."""
        current_location = self.get_current_location()
        if not current_location:
            return "You need to create a character first."
            
        exits = current_location.get("exits", [])
        if destination not in exits:
            return f"You can't go to {destination} from here. Available exits: {', '.join(exits)}"
            
        if destination not in self.locations:
            return f"{destination} is not a valid location."
            
        self.current_player.current_location = destination
        location = self.get_current_location()
        return f"You have arrived at {destination}.\n{location['description']}"

    def process_input(self, user_input: str, context: Dict[str, Any] = None) -> str:
        """Process user input and return a response."""
        if not context:
            context = {}
            
        if not user_input:
            return "Please enter a command."
            
        command = user_input.lower().strip()
        
        # Basic commands
        if command in ["look", "l"]:
            location = self.get_current_location()
            if not location:
                return "You need to create a character first."
                
            response = [f"You are in {self.current_player.current_location}."]
            response.append(location.get("dynamic_description", ""))
            
            if "exits" in location:
                response.append(f"Exits: {', '.join(location['exits'])}")
                
            if "npcs" in location:
                response.append(f"You see: {', '.join(location['npcs'])}")
                
            return "\n".join(response)
            
        elif command in ["inventory", "i"]:
            if not self.current_player:
                return "You need to create a character first."
                
            if not self.current_player.inventory:
                return "Your inventory is empty."
                
            items = [str(item) for item in self.current_player.inventory]
            return "Inventory:\n" + "\n".join(f"- {item}" for item in items)
            
        elif command.startswith("equip "):
            if not self.current_player:
                return "You need to create a character first."
                
            item_name = command[6:].strip()
            for item in self.current_player.inventory:
                if item.name.lower() == item_name.lower():
                    return self.current_player.equip_item(item)
            return f"You don't have '{item_name}' in your inventory."
            
        elif command in ["status", "stats"]:
            if not self.current_player:
                return "You need to create a character first."
                
            stats = [
                f"Name: {self.current_player.name}",
                f"Class: {self.current_player.character_class}",
                f"Level: {self.current_player.level}",
                f"HP: {self.current_player.hit_points}",
                "\nAttributes:"
            ]
            stats.extend(
                f"{attr.capitalize()}: {val}" 
                for attr, val in self.current_player.attributes.items()
            )
            return "\n".join(stats)
            
        elif command in ["help", "h"]:
            return """
Available Commands:
  look (l) - Look around your current location
  inventory (i) - Check your inventory
  equip [item] - Equip an item from your inventory
  status - Check your character's status
  go [direction] - Move to a new location
  talk [npc] - Talk to an NPC
  use [item] - Use an item from your inventory
  help (h) - Show this help message
  exit - Quit the game
"""
            
        elif command == "exit":
            return "Thank you for playing!"
            
        elif command.startswith("go "):
            if not self.current_player:
                return "You need to create a character first."
                
            destination = command[3:].strip()
            return self.move_player(destination)
            
        elif command.startswith("talk to"):
            npc_name = command[7:].strip()
            if not self.current_player:
                return "You need to create a character first."
                
            location = self.get_current_location()
            if npc_name in location.get("npcs", []):
                npc_dialogue = self.groq_engine.generate_npc_dialogue(
                    npc_name, 
                    self.current_player.name, 
                    self.current_player.current_location
                )
                return npc_dialogue
            return f"{npc_name} is not here."
            
        return f"I don't understand '{command}'. Type 'help' for a list of commands."

    def handle_attack(self) -> str:
        """Handle player attack during combat."""
        if not self.current_enemy:
            return "No enemy to attack!"
            
        # Calculate attack roll
        roll = random.randint(1, 20)
        hit_bonus = self.current_player.attributes.get("strength", 0) + self.rules["squad_tactics.json"]["combat"]["hit_bonus"]
        total_roll = roll + hit_bonus
        
        # Check if hit
        if total_roll >= 10:  # Base AC
            damage = self.current_player.attributes.get("strength", 0) + self.rules["squad_tactics.json"]["combat"]["damage_bonus"]
            self.current_enemy.hit_points -= damage
            
            if self.current_enemy.hit_points <= 0:
                self.end_combat("You defeated the enemy!")
                return "You strike a killing blow! The enemy falls to the ground."
                
            return f"You hit the {self.current_enemy.name} for {damage} damage!"
        
        return f"You miss the {self.current_enemy.name}!"

    def end_combat(self, message: str) -> str:
        """End combat mode with a message."""
        self.combat_mode = False
        self.current_enemy = None
        return message

    def show_inventory(self):
        """Display the player's inventory in a formatted way."""
        if not self.current_player:
            return "No player character selected"

        output = [
            "=" * 50,
            "Inventory:",
            "=" * 50,
            f"\nWeight: {self.current_player.inventory_weight}/{self.current_player.max_inventory_weight} kg",
            "-" * 50,
            "\nEquipped:",
            "-" * 10,
            f"Weapon: {self.current_player.equipped['weapon'].name if self.current_player.equipped['weapon'] else 'None'}",
            f"Armor: {self.current_player.equipped['armor'].name if self.current_player.equipped['armor'] else 'None'}"
        ]

        if self.current_player.equipped["accessories"]:
            output.append("\nAccessories:")
            for acc in self.current_player.equipped["accessories"]:
                output.append(f"- {acc.name}")
        else:
            output.append("\nAccessories: None")

        output.append("\nInventory Items:")
        for item in self.current_player.inventory:
            output.append(f"- {item}")

        return "\n".join(output)

    def equip_item(self, item_name: str) -> str:
        """Equip an item from inventory."""
        if not self.current_player:
            return "No player character selected"

        item = next((i for i in self.current_player.inventory if i.name.lower() == item_name.lower()), None)
        if not item:
            return f"No item named '{item_name}' in inventory"

        return self.current_player.equip_item(item)

    def unequip_item(self, slot: str) -> str:
        """Unequip an item from a specific slot."""
        if not self.current_player:
            return "No player character selected"

        if slot not in self.current_player.equipped:
            return f"Invalid slot: {slot}"

        item = self.current_player.equipped[slot]
        if not item:
            return f"No item equipped in {slot}"

        self.current_player.equipped[slot] = None
        return f"Unequipped {item.name} from {slot}"

    def examine_item(self, item_name: str) -> str:
        """Examine an item in detail."""
        if not self.current_player:
            return "No player character selected"

        item = next((i for i in self.current_player.inventory if i.name.lower() == item_name.lower()), None)
        if not item:
            return f"No item named '{item_name}' in inventory"

        return f"""
Examining {item.name}:
Type: {item.item_type}
Weight: {item.stats.get('weight', 0)} kg
Attributes: {json.dumps(item.stats, indent=2)}
"""

def display_header():
    print("\n" + "=" * 80)
    print("Dungeon Master RPG")
    print("=" * 80)
    print()

def display_character_info(player: Character):
    print("Player Info:")
    print(f"Name: {player.name}")
    print(f"Class: {player.character_class}")
    print(f"Level: {player.level}")
    print(f"HP: {player.hit_points}")
    print("\nAttributes:")
    for attr, value in player.attributes.items():
        print(f"{attr.capitalize()}: {value}")
    print()

def display_inventory(player: Character):
    print("Inventory:")
    if not player.inventory:
        print("Empty")
        return
    
    for item in player.inventory:
        print(f"- {item.name} ({item.item_type})")
    print()

def display_main_menu():
    print("\nMain Menu:")
    print("1. Move to new location")
    print("2. View inventory")
    print("3. Equip item")
    print("4. View character info")
    print("5. Look around")
    print("6. Talk to someone")
    print("7. Exit game")
    print()

if __name__ == '__main__':
    display_header()
    print("Welcome to the Text RPG!")
    game = RPGGame()
    
    # Character creation
    print("\n--- Character Creation ---")
    while True:
        name = input("Enter your character's name: ").strip()
        if name:
            break
            
    while True:
        char_class = input("Choose your class (Warrior, Mage, Rogue): ").strip()
        if char_class.lower() in ['warrior', 'mage', 'rogue']:
            break

    player = game.create_character(name, char_class)
    print(f"\nWelcome, {player.name} the {player.character_class}!")
    print(game.show_inventory())
    
    # Main game loop
    while True:
        user_input = input("\n> ").strip()
        if user_input.lower() == "exit":
            break
            
        response = game.process_input(user_input)
        print(response)
    
    print("\nThank you for playing!")
