import json
import os
from typing import Dict, Any
from game_objects import Character, Item
from dotenv import load_dotenv

class RPGGame:
    def __init__(self):
        self.rules = {}
        self.current_player = None
        self.current_enemy = None
        self.combat_mode = False

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

    def create_prompt(self, user_input: str, context: Dict[str, Any]) -> str:
        prompt = f"""
You are an expert Dungeon Master AI running a text-based RPG. Your responses must strictly comply with all official rule documents.

===== RULE DOCUMENTS =====

📘 rules.json:
{json.dumps(self.rules.get('rules.json', {}), indent=2)}

⚔️ squad_tactics.json:
{json.dumps(self.rules.get('squad_tactics.json', {}), indent=2)}

🧙 making_mercs.json:
{json.dumps(self.rules.get('making_mercs.json', {}), indent=2)}

🌍 building_worlds.json:
{json.dumps(self.rules.get('building_worlds.json', {}), indent=2)}

===== CURRENT CONTEXT =====
{json.dumps(context, indent=2)}

===== PLAYER ACTION =====
User said: {user_input}

===== YOUR INSTRUCTIONS =====
- ALWAYS follow the rules from all documents.
- DO NOT invent new rules or change stats/mechanics unless the rules allow it.
- Maintain game balance, immersive descriptions, and consistency.
- Respond as if you are the Dungeon Master running this world with full rule compliance.

Begin your narration below:
"""
        return prompt

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
                    prompt = self.create_prompt(user_input, context)
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
    game = RPGGame()
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
        print("Main Menu:\n1. Move to new location\n2. View inventory\n3. Equip item\n4. Unequip item\n5. Examine item\n6. View character info\n7. Look around\n8. Talk to someone\n9. Exit game")

        choice = input("\nEnter your choice (1-9): ")
        if choice == "1":
            user_input = input("\nEnter the location you want to move to: ")
        elif choice == "2":
            print(game.show_inventory())
            continue
        elif choice == "3":
            item_name = input("\nEnter the name of the item you want to equip: ")
            response = game.equip_item(item_name)
            print("\n", response)
            continue
        elif choice == "4":
            slot = input("\nEnter the slot to unequip (weapon/armor/accessory): ").lower()
            response = game.unequip_item(slot)
            print("\n", response)
            continue
        elif choice == "5":
            item_name = input("\nEnter the name of the item to examine: ")
            response = game.examine_item(item_name)
            print("\n", response)
            continue
        elif choice == "6":
            player = game.current_player
            print("\nPlayer Info:")
            print(f"Name: {player.name}\nClass: {player.character_class}\nLevel: {player.level}\nHP: {player.hit_points}\n")
            print("Attributes:")
            for attr, val in player.attributes.items():
                print(f"{attr.capitalize()}: {val}")
            continue
        elif choice == "7":
            user_input = "look"
        elif choice == "8":
            user_input = "talk"
        elif choice == "9":
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
