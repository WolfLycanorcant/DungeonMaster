import json
import os
import random
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from groq import Groq

class Item:
    def __init__(self, name: str, item_type: str, stats: Dict[str, Any], stackable: bool = False, max_stack: int = 1):
        self.name = name
        self.item_type = item_type
        self.stats = stats
        self.stackable = stackable
        self.max_stack = max_stack
        self.quantity = 1 if stackable else None
        
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
        valid_classes = ['Warrior', 'Mage', 'Rogue', 'enemy']
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

class RPGGame:
    def __init__(self):
        """Initialize the RPG game with default settings."""
        self.current_player = None
        self.current_enemy = None
        self.combat_mode = False
        self.groq_client = None
        self.rules = {}
        self.initialize_groq()
        self.initialize_game_data()
        self.load_rules()

    def initialize_groq(self):
        """Initialize the Groq client using environment variables."""
        load_dotenv()
        api_key = os.getenv('GROQ_API_KEY')
        model = os.getenv('GROQ_MODEL', 'mixtral-8x7b-instruct')
        
        if not api_key:
            print("Warning: GROQ_API_KEY not found in .env file. Some features may be limited.")
            return
        
        try:
            self.groq_client = Groq(api_key=api_key)
            self.groq_model = model
        except Exception as e:
            print(f"Warning: Failed to initialize Groq client: {e}")
            return
        
        # Test the connection
        try:
            test_response = self.groq_client.generate(
                model=self.groq_model,
                messages=[{"role": "user", "content": "Test connection"}],
                max_tokens=10
            )
            print("Groq client initialized successfully")
        except Exception as e:
            print(f"Warning: Failed to test Groq connection: {e}")

    def load_rules(self):
        """Load game rules from JSON files."""
        self.rules = {
            "rules.json": {
                "game_mechanics": {
                    "level_up_bonus": 5,
                    "xp_per_level": 1000
                }
            },
            "squad_tactics.json": {
                "combat": {
                    "hit_bonus": 2,
                    "damage_bonus": 1
                }
            },
            "making_mercs.json": {
                "character_creation": {
                    "base_attributes": 10,
                    "attribute_points": 5
                }
            },
            "building_worlds.json": {
                "world_generation": {
                    "max_locations": 10,
                    "npc_density": 0.5
                }
            }
        }

        filenames = ["rules.json", "squad_tactics.json", "making_mercs.json", "building_worlds.json"]
        for filename in filenames:
            try:
                with open(os.path.join("rules", filename), "r") as f:
                    self.rules[filename] = json.load(f)
            except Exception as e:
                print(f"Warning: Could not load {filename} - using default rules")

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
        """Get the current location details."""
        if not self.current_player:
            return {}
        return self.locations.get(self.current_player.current_location, {})

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

    def create_prompt_with_sensory_details(self, user_input: str, context: Dict[str, Any]) -> str:
        """Create a prompt with sensory details and rule compliance"""
        return f"""
You are an expert Dungeon Master AI running a text-based RPG. Every response MUST:
- Comply with all rules from the following JSON files:
  - rules.json
  - squad_tactics.json
  - making_mercs.json
  - building_worlds.json
- Maintain game balance and enforce all rule constraints.
- Describe the scene vividly using sensory perceptions (sight, sound, smell, feel).
- Mention all relevant NPCs and world objects present.
- End with a prompt asking the player what they want to do next.

========================= RULES =========================
📘 rules.json:
{json.dumps(self.rules.get('rules.json', {}), indent=2)}
⚔️ squad_tactics.json:
{json.dumps(self.rules.get('squad_tactics.json', {}), indent=2)}
🧙 making_mercs.json:
{json.dumps(self.rules.get('making_mercs.json', {}), indent=2)}
🌍 building_worlds.json:
{json.dumps(self.rules.get('building_worlds.json', {}), indent=2)}

====================== CONTEXT ========================
{json.dumps(context, indent=2)}

=================== PLAYER ACTION =====================
Player input: {user_input}

=================== YOUR RESPONSE =====================
"""

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
            response.append(location.get("description", ""))
            
            if "exits" in location:
                response.append(f"Exits: {', '.join(location['exits'])}")
                
            if "npcs" in location:
                response.append(f"You see: {', '.join(location['npcs'])}")
                
            if "enemies" in location and location["enemies"]:
                response.append(f"Danger! You spot: {', '.join(location['enemies'])}")
                
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
  attack - Attack an enemy (in combat)
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
                if hasattr(self, 'groq_client') and self.groq_client:
                    prompt = self.create_prompt_with_sensory_details(
                        f"Talk to {npc_name}",
                        {"current_location": self.current_player.current_location}
                    )
                    response = self.groq_client.generate(
                        model="mixtral-8x7b-instruct",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.7,
                        max_tokens=1000
                    )
                    return response.choices[0].message.content
                return f"You talk to {npc_name} and learn some interesting things."
            return f"{npc_name} is not here."
            
        elif self.combat_mode:
            if command.startswith("attack"):
                return self.handle_attack()
            elif command == "flee":
                return self.end_combat("You flee from combat!")
            
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

if __name__ == '__main__':
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
