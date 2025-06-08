import json
import os
import random
import sys
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from groq import Groq
from cachetools import LRUCache
import functools
import logging

# Basic logging configuration
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GroqEngine:
    def __init__(self):
        """Initialize the Groq AI engine."""
        load_dotenv()
        self.api_key = os.getenv('GROQ_API_KEY')
        self.description_cache = LRUCache(maxsize=128)
        self.model = os.getenv('GROQ_MODEL', 'llama3-8b-8192')
        self.client = None
        self.initialize()

    def initialize(self):
        """Initialize the Groq client."""
        if not self.api_key:
            logger.warning("GROQ_API_KEY not found in .env file. Some features may be limited.")
            return

        try:
            self.client = Groq(api_key=self.api_key)
            logger.info("Groq client initialized successfully")
            
            # Test the connection with a simple request
            # This generate call is a bit different, might need specific error handling or can be removed if not essential
            try:
                test_response = self.client.chat.completions.create( # Changed to chat.completions.create for consistency
                    model=self.model,
                    messages=[{"role": "user", "content": "Test connection"}],
                    max_tokens=10
                )
                logger.info("Groq model %s is accessible via chat completions.", self.model)
            except Exception as test_e: # More specific exception if possible
                 logger.warning("Failed test connection to Groq model %s via chat completions: %s", self.model, test_e)

        except Exception as e:
            logger.warning("Failed to initialize Groq client: %s", e)
            logger.warning("Make sure your API key has access to model: %s", self.model)

    def generate_description(self, context: Dict[str, Any]) -> str:
        """Generate a location description using Groq AI."""
        if not self.client:
            return "The location is dark and foreboding."

        cache_key_items = []
        if 'name' in context:
            cache_key_items.append(('name', context['name']))
        if 'description' in context:
            cache_key_items.append(('description', context['description']))
        if 'npcs' in context and isinstance(context['npcs'], list):
            cache_key_items.append(('npcs', tuple(sorted(context['npcs']))))
        if 'enemies' in context and isinstance(context['enemies'], list):
            cache_key_items.append(('enemies', tuple(sorted(context['enemies']))))
        if 'exits' in context and isinstance(context['exits'], list):
            cache_key_items.append(('exits', tuple(sorted(context['exits']))))

        cache_key = tuple(sorted(cache_key_items))

        if cache_key in self.description_cache:
            return self.description_cache[cache_key]

        try:
            location_desc = context.get('description', 'Unknown location')
            prompt_details = f"Context: Location Name: {context.get('name', 'N/A')}, NPCs: {context.get('npcs', [])}, Exits: {context.get('exits', [])}."
            prompt = f"""
            You are a master Dungeon Master. Describe this location:
            {location_desc}
            {prompt_details}
            
            Provide a vivid, immersive description that includes:
            - Sensory details
            - Points of interest
            - Environmental conditions
            - Potential dangers
            """

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a master Dungeon Master. Provide vivid, immersive descriptions of locations."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            if not response or not hasattr(response, 'choices') or not response.choices:
                logger.warning("Invalid response from Groq for location description.")
                return "The location is dark and foreboding."
                
            content = response.choices[0].message.content
            self.description_cache[cache_key] = content
            return content
        except Exception as e:
            logger.warning("Failed to generate location description: %s", e)
            return "The location is dark and foreboding."

    @functools.lru_cache(maxsize=128)
    def generate_npc_dialogue(self, npc_name: str, player_name: str, location: str) -> str:
        """Generate NPC dialogue using Groq AI."""
        if not self.client:
            return f"Hello, {player_name}. Welcome to {location}."

        try:
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
            
            if not response or not hasattr(response, 'choices') or not response.choices:
                logger.warning("Invalid response from Groq for NPC dialogue.")
                return f"Hello, {player_name}. Welcome to {location}."
                
            return response.choices[0].message.content
        except Exception as e:
            logger.warning("Failed to generate NPC dialogue for %s: %s", npc_name, e)
            return f"Hello, {player_name}. Welcome to {location}."

    @functools.lru_cache(maxsize=128)
    def generate_action_description(self, player_tuple: tuple, action: str) -> str:
        """Generate a description of the player's action using Groq AI.
        player_tuple should be a hashable representation of essential player attributes.
        Example: (player_name, player_class, player_level)
        """
        if not self.client:
            return f"The action '{action}' happens without incident."

        player_description = f"Player: Name: {player_tuple[0]}, Class: {player_tuple[1]}, Level: {player_tuple[2]}"

        try:
            prompt = f"""
            You are a master Dungeon Master. Describe the outcome of this player action:
            {player_description}
            Action: {action}
            
            Describe vividly:
            - The action performed
            - Immediate consequences or effects
            - Relevant environmental interactions

            Keep it immersive, dynamic, and concise (1-2 sentences).
            """

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a master Dungeon Master. Describe player actions vividly and concisely."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            if not response or not hasattr(response, 'choices') or not response.choices:
                logger.warning("Invalid response from Groq for action description.")
                return f"The action '{action}' occurs."
                
            return response.choices[0].message.content
        except Exception as e:
            logger.warning("Failed to generate action description for action '%s': %s", action, e)
            return f"The action '{action}' leads to unexpected results."

    @functools.lru_cache(maxsize=128)
    def generate_combat_description(self, player_tuple: tuple, enemy_tuple: tuple) -> str:
        """
        Generate a description of a combat scenario using Groq AI.
        player_tuple: (name, class, level, current_hp)
        enemy_tuple: (name, level, current_hp)
        """
        if not self.client:
            return "The clash of steel rings out!"

        player_desc = f"Player: {player_tuple[0]} ({player_tuple[1]} Lvl {player_tuple[2]}, HP: {player_tuple[3]})"
        enemy_desc = f"Enemy: {enemy_tuple[0]} (Lvl {enemy_tuple[1]}, HP: {enemy_tuple[2]})"

        try:
            prompt = f"""
            You are a master Dungeon Master. Describe this combat moment vividly:
            {player_desc} is fighting {enemy_desc}.
            Focus on the action, the environment, and the tension. Keep it concise (1-2 sentences).
            Example: {player_tuple[0]} lunges with a wild swing, but the {enemy_tuple[0]} sidesteps with a guttural snarl!
            """

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a master Dungeon Master. Describe combat moments vividly and concisely."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8, # Slightly higher for more varied combat descriptions
                max_tokens=150  # Enough for a couple of engaging sentences
            )

            if not response or not hasattr(response, 'choices') or not response.choices:
                logger.warning("Invalid response from Groq for combat description.")
                return "The battle rages on!"

            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning("Failed to generate combat description: %s", e)
            return "Sparks fly as weapons meet!"

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

    def format_status(self) -> str:
        """Format character status in a readable way using list join."""
        parts = []
        
        # Character info
        parts.append("=== Character Info ===")
        parts.append(f"Name: {self.name}")
        parts.append(f"Class: {self.character_class}")
        parts.append(f"Level: {self.level}")
        parts.append(f"HP: {self.hit_points}")
        parts.append("")
        
        # Attributes
        parts.append("=== Attributes ===")
        for attr, value in self.attributes.items():
            parts.append(f"{attr.capitalize()}: {value}")
        parts.append("")
        
        # Inventory
        parts.append("=== Inventory ===")
        if not self.inventory:
            parts.append("Inventory is empty")
        else:
            for item in self.inventory:
                parts.append(f"- {item}") # Relies on Item.__str__
        parts.append("")
        
        # Equipment
        parts.append("=== Equipment ===")
        weapon_name = self.equipped["weapon"].name if self.equipped["weapon"] else "None"
        armor_name = self.equipped["armor"].name if self.equipped["armor"] else "None"
        parts.append(f"Weapon: {weapon_name}")
        parts.append(f"Armor: {armor_name}")

        parts.append("Accessories:")
        if self.equipped['accessories']:
            for accessory in self.equipped['accessories']:
                parts.append(f"- {accessory.name}")
        else:
            parts.append("  None") # Indent "None" for accessories for clarity
        
        return "\n".join(parts)
    
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

class LazyRuleLoader:
    def __init__(self, rules_dir_path: str):
        self.rules_dir_path = rules_dir_path
        self._loaded_rules: Dict[str, Any] = {}
        if not os.path.isdir(self.rules_dir_path):
            # Create the directory if it doesn't exist
            try:
                os.makedirs(self.rules_dir_path)
                logger.info("Rules directory '%s' created.", self.rules_dir_path)
            except OSError as e:
                logger.warning("Could not create rules directory '%s': %s", self.rules_dir_path, e)
                # Depending on desired behavior, could raise an error or proceed with an empty loader
                # For now, it will proceed, and attempts to load files will fail gracefully.

    def __getitem__(self, rule_filename: str) -> Dict[str, Any]:
        if rule_filename not in self._loaded_rules:
            filepath = os.path.join(self.rules_dir_path, rule_filename)
            try:
                with open(filepath, 'r') as f:
                    self._loaded_rules[rule_filename] = json.load(f)
            except FileNotFoundError:
                logger.warning("Rule file '%s' not found.", filepath)
                self._loaded_rules[rule_filename] = {} # Return empty dict if file not found
            except json.JSONDecodeError:
                logger.warning("Could not decode JSON from '%s'.", filepath)
                self._loaded_rules[rule_filename] = {} # Return empty dict if JSON is invalid
        return self._loaded_rules[rule_filename]

    def __setitem__(self, key: str, value: Any):
        raise NotImplementedError("Rules are read-only after initial definition.")

    def __delitem__(self, key: str):
        raise NotImplementedError("Rules are read-only and cannot be deleted.")

    def keys(self) -> List[str]:
        try:
            return [f for f in os.listdir(self.rules_dir_path) if f.endswith('.json')]
        except FileNotFoundError:
            logger.warning("Rules directory '%s' not found when trying to list keys.", self.rules_dir_path)
            return []

    def __iter__(self):
        return iter(self.keys())

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self.__getitem__(key)
        except KeyError: # Should be handled by __getitem__ returning {}
            return default if default is not None else {}


class RPGGame:
    def __init__(self):
        """Initialize the RPG game with default settings."""
        self.current_player = None
        self.current_enemy = None
        self.combat_mode = False
        self.groq_engine = GroqEngine()
        self.rules = LazyRuleLoader("Json Files") # Use LazyRuleLoader
        self.session_history = []
        self.current_weather = None
        self.current_time = "morning"
        self._current_location_cache = None
        self._last_known_player_location = None
        
        self.command_handlers = self._initialize_command_handlers()

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
        # self.load_rules() # Removed: Rules are now loaded lazily
        
        # Initialize Groq if available
        if self.groq_engine.client:
            logger.info("Groq AI initialized successfully via RPGGame.")
        else:
            logger.warning("Groq AI not available. Some features may be limited. (RPGGame)")

    def _initialize_command_handlers(self) -> Dict[str, callable]:
        handlers = {
            "look": self._handle_look, "l": self._handle_look,
            "inventory": self._handle_inventory, "i": self._handle_inventory,
            "status": self._handle_status, "stats": self._handle_status,
            "equip": self._handle_equip,
            "go": self._handle_go, "move": self._handle_go,
            "talk": self._handle_talk, "speak": self._handle_talk,
            "help": self._handle_help, "h": self._handle_help,
            "exit": self._handle_exit, "quit": self._handle_exit,
            # Numeric commands will be mapped within process_input or can be added here
            "1": self._handle_look, # Mapping numeric choice to existing handler
            "2": self._handle_inventory,
            "3": lambda args: "Type the name of the item you want to equip (e.g., 'equip iron sword')", # Placeholder if equip needs args
            "4": self._handle_status,
            "5": self._handle_look, # Same as 1
            "6": lambda args: "Type the name of the NPC you want to talk to (e.g., 'talk to merchant')", # Placeholder if talk needs args
            "7": self._handle_exit,
        }
        return handlers

    def _handle_look(self, args: List[str]) -> str:
        if not self.current_player:
            return "You need to create a character first."
        location_details = self.get_current_location()
        if not location_details:
            return "Could not retrieve location details."

        response_parts = [f"You are in {self.current_player.current_location}."]
        response_parts.append(location_details.get("dynamic_description", "It's hard to make out any details."))

        if "exits" in location_details:
            response_parts.append(f"Exits: {', '.join(location_details['exits'])}")
        if location_details.get("npcs"):
            response_parts.append(f"You see: {', '.join(location_details['npcs'])}")
        else:
            response_parts.append("You see no one of interest here.")
        return "\n".join(response_parts)

    def _handle_inventory(self, args: List[str]) -> str:
        if not self.current_player:
            return "You need to create a character first."
        if not self.current_player.inventory:
            return "Your inventory is empty."
        items = [str(item) for item in self.current_player.inventory]
        return "Inventory:\n" + "\n".join(f"- {item}" for item in items)

    def _handle_status(self, args: List[str]) -> str:
        if not self.current_player:
            return "You need to create a character first."
        return self.current_player.format_status()

    def _handle_equip(self, args: List[str]) -> str:
        if not self.current_player:
            return "You need to create a character first."
        if not args:
            return "What would you like to equip?"
        item_name = " ".join(args)
        for item in self.current_player.inventory:
            if item.name.lower() == item_name.lower():
                # Assuming Character.equip_item returns a string response
                return self.current_player.equip_item(item)
        return f"You don't have '{item_name}' in your inventory."

    def _handle_go(self, args: List[str]) -> str:
        if not self.current_player:
            return "You need to create a character first."
        if not args:
            return "Where would you like to go?"
        destination = " ".join(args)
        return self.move_player(destination) # move_player itself handles logic and returns string

    def _handle_talk(self, args: List[str]) -> str:
        if not self.current_player:
            return "You need to create a character first."
        if not args:
            return "Who would you like to talk to?"

        npc_name = " ".join(args)
        # npc_name should be extracted carefully if it's multi-word and part of a phrase like "talk to [npc name]"
        # For now, assuming args directly contains the NPC name.

        location_details = self.get_current_location()
        if not location_details or not location_details.get("npcs"):
            return f"{npc_name} is not here, or there's no one to talk to."

        # Case-insensitive check
        found_npc = None
        for npc_in_loc in location_details.get("npcs", []):
            if npc_in_loc.lower() == npc_name.lower():
                found_npc = npc_in_loc
                break

        if found_npc:
            return self.groq_engine.generate_npc_dialogue(
                found_npc,
                self.current_player.name,
                self.current_player.current_location
            )
        return f"{npc_name} is not here."

    def _handle_help(self, args: List[str]) -> str:
        # This help message might need to be updated based on command parsing changes
        return """
Available Commands:
  look (l)             - Look around your current location
  inventory (i)        - Check your inventory
  status (stats)       - Check your character's status
  equip [item name]    - Equip an item from your inventory
  go [direction/place] - Move to a new location
  talk [npc name]      - Talk to an NPC
  help (h)             - Show this help message
  exit / quit          - Quit the game
Numerical choices from menus are also accepted.
"""

    def _handle_exit(self, args: List[str]) -> str:
        # print("Thank you for playing! Goodbye!") # Side effect, better handled by caller if needed
        # sys.exit(0) # Avoid sys.exit within game logic if possible
        return "EXIT_GAME_REQUESTED"


    def process_input(self, user_input: str, context: Dict[str, Any] = None) -> str:
        """Process user input using command handlers."""
        if not user_input:
            return "Please enter a command."
            
        # Basic parsing: split the input into a command word and arguments
        parts = user_input.strip().lower().split()
        if not parts:
            return "Please enter a command."
            
        command_word = parts[0]
        args = parts[1:]

        # Handle numeric choices that were previously direct if-elif
        # These are now mapped in self.command_handlers initialization
        if command_word in self.command_handlers and command_word.isdigit():
            handler = self.command_handlers[command_word]
            # For numeric commands that are placeholders for more complex input (e.g., equip, talk)
            # the lambda functions in _initialize_command_handlers return instructional messages.
            # For others like '1' (look), '2' (inventory), they directly call the respective handlers.
            if command_word == "3": # Equip prompt
                 return handler(args) # This lambda returns the prompt string
            elif command_word == "6": # Talk prompt
                 return handler(args) # This lambda returns the prompt string
            return handler(args) # For 1, 2, 4, 5, 7 which map to direct actions

        # Handle text commands
        # Special case for "talk to <npc>" vs "talk <npc>"
        if command_word == "talk" and args and args[0] == "to": # e.g. "talk to merchant"
            args = args[1:] # Remove "to", new args is ["merchant"]

        handler = self.command_handlers.get(command_word)
        if handler:
            return handler(args)

        # If no specific handler, try the generic action description
        # This part might need adjustment based on how actions vs commands are differentiated
        if self.current_player:
            player_tuple = (
                self.current_player.name,
                self.current_player.character_class,
                self.current_player.level
            )
            # Pass the original, un-lowercased, stripped input for more natural AI descriptions
            return self.groq_engine.generate_action_description(player_tuple, user_input.strip())
            
        return f"I don't understand '{user_input}'. Type 'help' for a list of commands."

    # def load_rules(self): # This method is no longer needed due to LazyRuleLoader
    #     """Load all rule files from the Json Files directory."""
    #     rules_dir = "Json Files"
    #     for filename in os.listdir(rules_dir):
    #         if filename.endswith('.json'):
    #             try:
    #                 with open(os.path.join(rules_dir, filename), 'r') as f:
    #                     self.rules[filename] = json.load(f) # Now handled by LazyRuleLoader
    #             except Exception as e:
    #                 print(f"Warning: Failed to load {filename}: {e}")

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

    # build_prompt method removed as it's no longer used.
    # AI prompts are now generated directly within the specific GroqEngine methods
    # (generate_description, generate_npc_dialogue, generate_action_description, generate_combat_description).

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
            logger.error("Error creating character: %s", e)
            return None

    def get_current_location(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Get the current location details. Uses a cache that can be refreshed."""
        if not self.current_player:
            return {}

        # Check cache first
        if not force_refresh and \
           self._current_location_cache and \
           self.current_player.current_location == self._last_known_player_location:
            return self._current_location_cache

        # If cache miss, refresh is forced, or player has moved, fetch new data
        location_name = self.current_player.current_location
        base_location_data = self.locations.get(location_name, {})

        if not base_location_data:
            logger.warning("Location data for '%s' not found in self.locations.", location_name)
            self._current_location_cache = {
                "name": location_name,
                "description": "An unknown area.",
                "dynamic_description": "It's an unfamiliar place."
            }
            self._last_known_player_location = location_name
            return self._current_location_cache

        context_for_description = {
            "name": location_name,
            "description": base_location_data.get("description", "A place with no base description."),
            "npcs": base_location_data.get("npcs", []),
            "enemies": base_location_data.get("enemies", []),
            "exits": base_location_data.get("exits", [])
        }

        dynamic_description = self.groq_engine.generate_description(context_for_description)

        self._current_location_cache = dict(base_location_data)
        self._current_location_cache["name"] = location_name
        self._current_location_cache["dynamic_description"] = dynamic_description
        self._last_known_player_location = location_name

        return self._current_location_cache

    def move_player(self, destination: str) -> str:
        """Move the player to a new location if it's a valid destination."""
        # Get current location (uses cache unless player moved previously and it wasn't refreshed)
        current_location_data = self.get_current_location()
        if not current_location_data:  # Handles if current_player is None via get_current_location
            return "You need to create a character first."

        # Check if destination is a valid exit from current location
        exits = current_location_data.get("exits", [])
        if destination not in exits:
            return f"You can't go to {destination} from here. Available exits: {', '.join(exits)}"

        # Check if destination is a valid location
        if destination not in self.locations:
            return f"{destination} is not a valid location."

        # Update player's location
        self.current_player.current_location = destination

        # Clear the location cache since we're moving to a new location
        self._current_location_cache = None

        # Get the new location's data
        new_location = self.get_current_location(force_refresh=True)
        if not new_location:
            return f"You arrive at {destination}, but something seems off..."

        # Build the response
        response_parts = [f"You move to {destination}."]

        # Add location description if available
        if "description" in new_location:
            response_parts.append(new_location["description"])

        # Add visible exits if available
        if "exits" in new_location and new_location["exits"]:
            response_parts.append(f"Exits: {', '.join(new_location['exits'])}")

        # Add NPCs if present
        if "npcs" in new_location and new_location["npcs"]:
            response_parts.append(f"You see: {', '.join(new_location['npcs'])}")

        # Update the last known location
        self._last_known_player_location = destination

        # Update session memory with the move action
        self.update_session_memory(
            f"moved to {destination}",
            f"Arrived at {destination}. {new_location.get('description', '')}"
        )

        return "\n".join(response_parts)

        # Generic action processing for commands not handled above
        # Define command prefixes that constitute a general player action
        action_prefixes = ["attack", "use", "cast", "open", "climb", "read", "give", "take", "drop", "examine"]
        # Exclude commands that are definitely not single turn actions handled by generate_action_description
        non_action_commands = ["go", "talk", "look", "inventory", "status", "help", "exit", "equip"]

        is_general_action = False
        if not any(command.startswith(nac) for nac in non_action_commands): # if not a navigation/meta command
            if any(command.startswith(ap) for ap in action_prefixes): # and is an action type command
                 is_general_action = True
            elif len(command.split()) == 1 and command not in non_action_commands: # also consider single word commands as actions if not meta
                is_general_action = True


        if self.current_player and is_general_action:
            player_tuple = (
                self.current_player.name,
                self.current_player.character_class,
                self.current_player.level
            )
            # 'command' is the raw user input string, e.g., "attack goblin" or "examine sword"
            return self.groq_engine.generate_action_description(player_tuple, command)
            
        return f"I don't understand '{command}'. Type 'help' for a list of commands."

    def handle_attack(self) -> str:
        """Handle player attack during combat."""
        if not self.current_enemy:
            return "No enemy to attack!"
            
        # Calculate attack roll
        roll = random.randint(1, 20)
        # Access squad_tactics.json through LazyRuleLoader
        squad_tactics_rules = self.rules["squad_tactics.json"]
        if not squad_tactics_rules: # Handle case where rule file failed to load
             logger.warning("squad_tactics.json rules not available for combat.")
             hit_bonus = self.current_player.attributes.get("strength", 0) # Default bonus
             damage = self.current_player.attributes.get("strength", 0) # Default damage
        else:
            hit_bonus = self.current_player.attributes.get("strength", 0) + squad_tactics_rules.get("combat", {}).get("hit_bonus", 0)
            damage = self.current_player.attributes.get("strength", 0) + squad_tactics_rules.get("combat", {}).get("damage_bonus", 0)

        total_roll = roll + hit_bonus
        
        # Check if hit
        if total_roll >= 10:  # Base AC
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
        """Display the player's inventory in a formatted way using list join."""
        if not self.current_player:
            return "No player character selected"

        parts = []
        parts.append("=" * 50)
        parts.append("Inventory:")
        parts.append("=" * 50)
        # Note: f-string with \n might be okay, but for consistency, could also be separate appends.
        # For this specific line, f-string is fine as it's a single conceptual unit.
        parts.append(f"\nWeight: {self.current_player.inventory_weight}/{self.current_player.max_inventory_weight} kg")
        parts.append("-" * 50)

        parts.append("\nEquipped:") # Leading newline for spacing
        parts.append("-" * 10)
        weapon_name = self.current_player.equipped["weapon"].name if self.current_player.equipped["weapon"] else "None"
        armor_name = self.current_player.equipped["armor"].name if self.current_player.equipped["armor"] else "None"
        parts.append(f"Weapon: {weapon_name}")
        parts.append(f"Armor: {armor_name}")

        parts.append("\nAccessories:") # Leading newline for spacing
        if self.current_player.equipped["accessories"]:
            for acc in self.current_player.equipped["accessories"]:
                parts.append(f"- {acc.name}")
        else:
            parts.append("  None") # Indent "None"

        parts.append("\nInventory Items:") # Leading newline for spacing
        if self.current_player.inventory:
            for item in self.current_player.inventory:
                parts.append(f"- {item}") # Relies on Item.__str__
        else:
            parts.append("  Your inventory is empty.") # Indent for clarity

        return "\n".join(parts)



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
    print("\nType 'help' to see the main menu")
    
    # Main game loop
    while True:
        display_main_menu()
        user_input = input("\n> ").strip()
        if user_input.lower() == "exit":
            break
            
        response = game.process_input(user_input)
        print(response)
    
    print("\nThank you for playing!")
