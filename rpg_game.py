import json
import os
from typing import Dict, Any
from game_objects import Character, Item
from dotenv import load_dotenv
from groq import Groq

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
                prompt = f"""
You are an expert Dungeon Master AI running a text-based RPG. Describe the current location and mission in an engaging way.

Current Location: {context['current_location']}
Description: {context['location_info']['description']}
Exits: {', '.join(context['location_info']['exits'])}
NPCs: {', '.join(context['location_info']['npcs'])}
Mission: {context['mission']}

Provide a vivid description of the environment and mission objectives.
"""
                response = game.groq.chat.completions.create(
                    model="mixtral-8x7b",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=300
                )
                print("\n" + response.choices[0].text + "\n")
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
            print("\nThanks for playing!")
            break
        else:
            print("\nInvalid choice. Please try again.")
            continue

        context = {
            "current_location": "Starting Town",
            "player": game.current_player
        }
        response = game.process_input(user_input, context)
        print("\n", response)

if __name__ == "__main__":
    main()
