import json
import os
import random
from typing import Dict, Any, List, Optional
from game_objects import Character, Item
from dotenv import load_dotenv
from groq import Groq

class RPGGame:
    def __init__(self):
        """Initialize the RPG game with default settings."""
        self.current_player = None
        self.current_enemy = None
        self.combat_mode = False
        self.groq_client = None
        self.initialize_groq()
        self.initialize_game_data()

    def initialize_groq(self):
        """Initialize the Groq client using environment variables."""
        load_dotenv()
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            print("Warning: GROQ_API_KEY not found in .env file. Some features may be limited.")
            return
        try:
            self.groq_client = Groq(api_key=api_key)
        except Exception as e:
            print(f"Warning: Failed to initialize Groq client: {e}")

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
                "enemies": ["Goblin", "Wolf", "Bandit"]
            },
            "Market Square": {
                "description": "A busy marketplace with various shops and stalls.",
                "exits": ["Starting Town", "Blacksmith", "Tavern"],
                "npcs": ["Merchant", "Blacksmith", "Innkeeper"]
            }
        }

    def create_character(self, name: str, character_class: str) -> Character:
        """Create a new character with the given name and class."""
        try:
            self.current_player = Character(name, character_class)
            # Add starting items based on class
            if character_class.lower() == "warrior":
                self.current_player.add_item(Item("Iron Sword", "weapon", {"attack": 5, "defense": 1}))
                self.current_player.add_item(Item("Leather Armor", "armor", {"defense": 3}))
            elif character_class.lower() == "mage":
                self.current_player.add_item(Item("Wooden Staff", "weapon", {"attack": 3, "magic": 5}))
                self.current_player.add_item(Item("Robe", "armor", {"defense": 1, "magic_defense": 3}))
            elif character_class.lower() == "rogue":
                self.current_player.add_item(Item("Dagger", "weapon", {"attack": 4, "critical": 2}))
                self.current_player.add_item(Item("Leather Armor", "armor", {"defense": 2, "evasion": 5}))
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
            
        return f"I don't understand '{command}'. Type 'help' for a list of commands."

def main():
    """Main game loop."""
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
        print("Invalid class. Please choose Warrior, Mage, or Rogue.")
    
    player = game.create_character(name, char_class)
    if not player:
        print("Failed to create character. Exiting...")
        return
        
    print(f"\nWelcome, {player.name} the {player.character_class}!")
    print("Type 'help' for a list of commands.\n")
    
    # Game loop
    while True:
        try:
            command = input("\n> ").strip().lower()
            if command in ['exit', 'quit']:
                print("Thank you for playing!")
                break
                
            response = game.process_input(command)
            print(f"\n{response}")
            
        except KeyboardInterrupt:
            print("\nUse 'exit' or 'quit' to leave the game.")
        except Exception as e:
            print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    main()

class RPGGame:
    def __init__(self):
        self.rules = {}
        self.current_player = None
        self.current_enemy = None
        self.combat_mode = False
        self.groq = None
        self.initialize_groq()

        self.initialize_game_data()
        self.load_rules()

    def initialize_game_data(self):
        self.locations = {
            "Starting Town": {
                "description": "A bustling town with cobblestone streets and wooden houses.",
                "exits": ["Forest", "Market Square"],
                "npcs": ["Shopkeeper", "Guard"]
            },
            "Forest": {
                "description": "A dense forest with tall trees and mysterious sounds.",
                "exits": ["Starting Town", "Cave Entrance"],
                "npcs": ["Forest Ranger", "Herbalist"]
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
            }
        }

    def load_rules(self):
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

    def initialize_groq(self):
        """Initialize Groq client with API key from .env"""
        load_dotenv()
        api_key = os.getenv('GROQ_API_KEY')
        if api_key:
            self.groq = Groq(api_key=api_key)

    def create_prompt_with_sensory_details(self, user_input: str, context: Dict[str, Any], rules: Dict[str, Any]) -> str:
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
{json.dumps(rules.get('rules.json', {}), indent=2)}
⚔️ squad_tactics.json:
{json.dumps(rules.get('squad_tactics.json', {}), indent=2)}
🧙 making_mercs.json:
{json.dumps(rules.get('making_mercs.json', {}), indent=2)}
🌍 building_worlds.json:
{json.dumps(rules.get('building_worlds.json', {}), indent=2)}

======================= CONTEXT ========================
{json.dumps(context, indent=2)}

==================== PLAYER ACTION =====================
Player input: {user_input}

==================== YOUR RESPONSE =====================
"""

    def process_input(self, user_input: str, context: Dict[str, Any]) -> str:
        try:
            user_input = user_input.lower()

            if self.combat_mode:
                if user_input.startswith("attack"):
                    return self.handle_attack()
                elif user_input == "flee":
                    return self.end_combat("You flee from combat!")

            if user_input.startswith("inventory"):
                return self.show_inventory()
            elif user_input.startswith("equip"):
                item_name = user_input.split(" ", 1)[1]
                return self.equip_item(item_name)
            elif user_input.startswith("unequip"):
                slot = user_input.split(" ", 1)[1]
                return self.unequip_item(slot)
            elif user_input.startswith("examine"):
                item_name = user_input.split(" ", 1)[1]
                return self.examine_item(item_name)
            elif user_input.startswith("go to"):
                location = user_input[6:].strip()
                if location in self.locations:
                    context["current_location"] = location
                    return f"You have arrived at {location}.\n{self.locations[location]['description']}"
                return "That location doesn't exist."
            elif user_input.startswith("talk to"):
                npc = user_input[7:].strip()
                if npc in self.locations[context["current_location"]]["npcs"]:
                    return f"You talk to {npc} and learn some interesting things."
                return "That NPC is not here."
            else:
                if hasattr(self, 'groq') and self.groq:
                    prompt = self.create_prompt_with_sensory_details(user_input, context, self.rules)
                    response = self.groq.generate(
                        model="mixtral-8x7b-instruct",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.7,
                        max_tokens=1000
                    )
                    return response.choices[0].message.content
                return f"You {user_input} and nothing much happens."

        except Exception as e:
            return f"An error occurred: {str(e)}"

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
        output.append("-" * 15)
        if not self.current_player.inventory:
            output.append("Empty")
        else:
            for item in self.current_player.inventory:
                output.append(str(item))

        output.append("=" * 50)
        return "\n".join(output)

    def equip_item(self, item_name: str):
        if not self.current_player:
            return "No player character selected"

        item = next((i for i in self.current_player.inventory if i.name.lower() == item_name.lower()), None)
        if not item:
            return f"Item '{item_name}' not found in inventory"

        result = self.current_player.equip_item(item)
        return result

    def unequip_item(self, slot: str):
        if not self.current_player:
            return "No player character selected"

        result = self.current_player.unequip_item(slot)
        return result

    def examine_item(self, item_name: str):
        if not self.current_player:
            return "No player character selected"

        item = self.current_player.get_item(item_name)
        if not item:
            return f"Item '{item_name}' not found in inventory"

        stats = ", ".join(f"{k}: {v}" for k, v in item.stats.items())
        return f"\n{item.name} ({item.item_type})\nStats: {stats}\nStackable: {item.stackable}\nMax Stack: {item.max_stack}\nQuantity: {item.quantity if item.stackable else 'N/A'}"

    def start_combat(self, enemy: Character) -> str:
        self.current_enemy = enemy
        self.combat_mode = True
        return f"Combat started with {enemy.name}!"

    def end_combat(self, message: str) -> str:
        self.current_enemy = None
        self.combat_mode = False
        return message

    def handle_attack(self) -> str:
        if not self.current_player or not self.current_enemy:
            return "No combat in progress"

        attack_roll = self.current_player.get_attack_bonus()
        defense_roll = self.current_enemy.get_defense_bonus()
        if attack_roll >= defense_roll:
            damage = max(1, attack_roll - defense_roll)
            self.current_enemy.hit_points -= damage
            if self.current_enemy.hit_points <= 0:
                return self.end_combat(f"You defeated {self.current_enemy.name}!")
            return f"You hit {self.current_enemy.name} for {damage} damage!"
        return f"You missed {self.current_enemy.name}!"

def main():
    # Initialize game and Groq
    game = RPGGame()
    if not game.groq:
        print("Warning: Groq API not initialized. Using basic descriptions.")
    
    starting_items = [
        Item("Short Sword", "weapon", {"bonus": 2, "weight": 2}, stackable=False),
        Item("Leather Armor", "armor", {"bonus": 1, "weight": 3}, stackable=False),
        Item("Healing Potion", "consumable", {"healing": 5, "weight": 1}, stackable=True, max_stack=5)
    ]

    print("=" * 80)
    print("Dungeon Master RPG")
    print("=" * 80)

    print("Welcome to the Dungeon Master RPG!")

    while True:
        if game.current_player is None:
            print("\nCharacter Creation:")
            name = input("Enter your character's name: ")
            character_class = input("Choose your class (Warrior, Mage, Rogue): ").capitalize()

            try:
                player = Character(name, character_class)
                for item in starting_items:
                    result = player.add_item(item)
                    print(result)
                game.current_player = player
                continue
            except ValueError as e:
                print(e)
                continue

        print("=" * 80)
        print(f"Current Location: Starting Town")
        
        # Create context for environment description
        context = {
            "current_location": "Starting Town",
            "player": game.current_player,
            "location_info": game.locations["Starting Town"],
            "mission": "Explore the town and gather supplies before venturing into the forest."
        }
        
        # Get environment description from Groq
        try:
            if game.groq:
                # Create a conversation history if it doesn't exist
                if not hasattr(game, 'conversation_history'):
                    game.conversation_history = []
                
                # Add the player's input to the conversation history
                game.conversation_history.append({"role": "user", "content": user_input})
                
                # Create the prompt with context and conversation history
                prompt = f"""
You are an expert Dungeon Master AI running a text-based RPG. Generate a response that:
1. Acknowledges the player's action: "{user_input}"
2. Describes the current location and environment
3. Maintains game balance and rules
4. Provides engaging sensory details
5. Keeps the story consistent

Current Location: {context['current_location']}
Description: {context['location_info']['description']}
Exits: {', '.join(context['location_info']['exits'])}
NPCs: {', '.join(context['location_info']['npcs'])}
Mission: {context['mission']}

Previous conversation:
{chr(10).join([f"{msg['role'].upper()}: {msg['content']}" for msg in game.conversation_history[-3:]])}

Player just said: {user_input}

Provide a vivid and engaging response that:
- Acknowledges the player's action
- Describes the environment
- Maintains game balance
- Provides sensory details
- Ends with a prompt asking what the player wants to do next
"""
                
                # Send the prompt with conversation history
                response = game.groq.chat.completions.create(
                    model="deepseek-r1-distill-llama-70b",
                    messages=[
                        {"role": "system", "content": "You are a helpful and engaging Dungeon Master AI. Always provide vivid descriptions and maintain game balance."},
                        *game.conversation_history,
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=300
                )
                
                # Add the AI's response to the conversation history
                game.conversation_history.append({"role": "assistant", "content": response.choices[0].message.content})
                
                print("\n" + response.choices[0].message.content + "\n")
            else:
                print(f"\n{game.locations['Starting Town']['description']}")
                print("\nMission: Explore the town and gather supplies before venturing into the forest.")
                print("Available exits:", ", ".join(game.locations['Starting Town']['exits']))
                print("NPCs present:", ", ".join(game.locations['Starting Town']['npcs']))
                print()
        except Exception as e:
            print(f"\nError generating description: {str(e)}")
            print(f"\n{game.locations['Starting Town']['description']}")
            print("\nMission: Explore the town and gather supplies before venturing into the forest.")
            print("Available exits:", ", ".join(game.locations['Starting Town']['exits']))
            print("NPCs present:", ", ".join(game.locations['Starting Town']['npcs']))
            print()
        # Define menu options as a dictionary
        menu_options = {
            "1": "move to new location",
            "2": "view inventory",
            "3": "equip item",
            "4": "unequip item",
            "5": "examine item",
            "6": "view character info",
            "7": "look around",
            "8": "talk to someone",
            "9": "exit game",
            "move": "1",
            "inventory": "2",
            "equip": "3",
            "unequip": "4",
            "examine": "5",
            "character": "6",
            "look": "7",
            "talk": "8",
            "exit": "9"
        }

        # Display equipped items first
        print("\nEquipped Items:")
        print("-" * 20)
        print(f"Weapon: {game.current_player.equipped['weapon'] if game.current_player.equipped['weapon'] else '[Empty]'}")
        print(f"Armor: {game.current_player.equipped['armor'] if game.current_player.equipped['armor'] else '[Empty]'}")
        print(f"Accessories: {', '.join(game.current_player.equipped['accessories']) if game.current_player.equipped['accessories'] else '[Empty]'}")
        print("-" * 20)

        print("\nMain Menu:")
        print("1. Move to new location")
        print("2. View inventory")
        print("3. Equip item")
        print("4. Unequip item")
        print("5. Examine item")
        print("6. View character info")
        print("7. Look around")
        print("8. Talk to someone")
        print("9. Exit game")

        choice = input("\nEnter your choice (1-9) or type the action: ").lower().strip()
        # Convert choice to number if it's a menu option
        if choice in menu_options:
            choice = menu_options[choice]
        
        if choice == "1" or choice == "move":
            user_input = input("\nEnter the location you want to move to: ")
        elif choice == "2" or choice == "inventory":
            print(game.show_inventory())
            continue
        elif choice == "3" or choice == "equip":
            item_name = input("\nEnter the name of the item you want to equip: ")
            response = game.equip_item(item_name)
            print("\n", response)
            continue
        elif choice == "4" or choice == "unequip":
            slot = input("\nEnter the slot to unequip (weapon/armor/accessory): ").lower()
            response = game.unequip_item(slot)
            print("\n", response)
            continue
        elif choice == "5" or choice == "examine":
            item_name = input("\nEnter the name of the item to examine: ")
            response = game.examine_item(item_name)
            print("\n", response)
            continue
        elif choice == "6" or choice == "character":
            player = game.current_player
            print("\nPlayer Info:")
            print(f"Name: {player.name}\nClass: {player.character_class}\nLevel: {player.level}\nHP: {player.hit_points}\n")
            print("Attributes:")
            for attr, val in player.attributes.items():
                print(f"{attr.capitalize()}: {val}")
            continue
        elif choice == "7" or choice == "look":
            user_input = "look"
        elif choice == "8" or choice == "talk":
            user_input = "talk"
        elif choice == "9" or choice == "exit":
            print("\nThank you for playing! Goodbye!")
            break
