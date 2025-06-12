# Dungeon Master RPG

A text-based RPG game with Groq AI integration, built with Python and Flask. Experience a dynamic adventure with rich character progression and interactive gameplay.

## Features

- **Character System**
  - Create characters with unique classes (Warrior, Mage, Rogue)
  - Detailed character attributes and progression
  - Visual character status panel with health, mana, and experience bars
  - Equipment management with weapon, armor, and accessory slots

- **Gameplay**
  - Dynamic world generation with Groq AI
  - Real-time combat system with turn-based mechanics
  - Interactive NPCs with AI-powered dialogue
  - Location-based exploration with unique encounters
  - Enemy encounters with varying difficulty levels

- **Inventory & Items**
  - Comprehensive inventory management system
  - Item categories (weapons, armor, consumables, quest items)
  - Item details including value, weight, and special properties
  - Equipment comparison and quick-equip functionality

- **User Interface**
  - Responsive design that works on desktop and tablet
  - Interactive panels for character status and inventory
  - Visual progress indicators for health, mana, and experience
  - Tooltips and help text for game mechanics

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your Groq API key:
```
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=mixtral-8x7b-instruct
```

3. Start the server:
```bash
./start.bat
```

The game will be available at http://localhost:30000

## Game Controls

### Character Management
- Click "Start New Game" to create a new character
- Select your character class (Warrior, Mage, or Rogue)
- Click "Character Status" to view your character's stats and equipment
- Use the inventory panel to manage your items and equipment

### Combat
- Click "Start Combat" to begin a battle
- Use "Player Attack" to attack enemies
- Special abilities unlock as you level up
- Monitor your health and mana during combat

### Exploration
- Explore different locations in the world
- Discover hidden items and secrets
- Interact with the environment

### NPC Interaction
- Talk to NPCs for quests and information
- Complete quests to earn rewards
- Build relationships with different factions

### Inventory & Equipment
- Drag and drop items to equip/unequip
- Sort and filter your inventory
- Check item details by hovering over them
- Compare equipment stats before equipping

## Game Mechanics

### Character Progression
- Gain experience points (XP) through combat and quests
- Level up to increase attributes and unlock abilities
- Each class has unique skill trees and playstyles
- Attribute points can be allocated on level up

### Combat System
- Turn-based combat with initiative order
- Different attack types (melee, ranged, magic)
- Status effects and conditions (poison, stun, etc.)
- Critical hits and special abilities

### Inventory System
- Weight-based carrying capacity
- Item rarity system (common, uncommon, rare, epic, legendary)
- Stackable items where applicable
- Quick slots for frequently used items

### World Interaction
- Dynamic day/night cycle
- Weather system affecting gameplay
- NPC schedules and routines
- Interactive objects in the environment

### Recent Updates
- Added visual character status panel
- Implemented detailed inventory management
- Enhanced equipment comparison
- Improved UI/UX with tooltips and help text
- Added support for item tooltips and detailed descriptions
- Implemented responsive design for different screen sizes
- Groq AI generates dynamic content for locations and NPC dialogue

## Project Structure

```
Dungeon Master/
├── Server/
│   ├── app.py          # Flask application
│   └── templates/      # HTML templates
├── game.py            # Game logic and character classes
├── requirements.txt   # Project dependencies
├── start.bat         # Start script
└── .env             # Environment variables
```

## Technology Stack

- Python 3.x
- Flask
- Groq AI
- HTML/CSS/JavaScript

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
