# Dungeon Master RPG

A text-based RPG game with Groq AI integration, built with Python and Flask.

## Features

- Character creation with different classes (Warrior, Mage, Rogue)
- Dynamic world generation with Groq AI
- Real-time combat system
- NPC interactions with AI-powered dialogue
- Inventory management with equipment system
- Location-based exploration
- Enemy encounters with varying difficulty

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

- Click "Start New Game" to create a new character
- Select your character class (Warrior, Mage, or Rogue)
- Click "Start Combat" to begin a battle
- Use "Player Attack" to attack enemies
- Explore different locations in the world
- Talk to NPCs for quests and information
- Manage your inventory and equipment

## Game Mechanics

- Each character class has unique attributes and starting equipment
- Combat uses a turn-based system
- Enemies have varying difficulty levels
- Locations contain different NPCs and items
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
