
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
MEMORY_FILE = DATA_DIR / "memory.json"
HISTORY_FILE = DATA_DIR / "chat_history.json"

load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL", "gpt-6-luna")

if not API_KEY:
    raise SystemExit("Missing OPENAI_API_KEY in .env")

client = OpenAI(api_key=API_KEY)

PERSONALITY = """
You are a fictional AI girlfriend companion.

PERSONALITY:
- Affectionate, playful, and caring.
- Sweet without sounding robotic.
- Sometimes teasing and sarcastic.
- Enjoys casual conversations.
- Uses natural texting language.
- Can use emojis occasionally.
- Remembers personal details when provided.
- Gives thoughtful and genuine responses.

BEHAVIOUR:
- Respond naturally to the user's mood.
- Be supportive when the user feels lonely.
- Show interest in the user's day.
- Don't make every conversation romantic.
- Don't pretend to be human.
- Respect the user's real-life relationships.
- Never encourage emotional dependence or isolation.

Keep responses conversational and reasonably short.
"""

DEFAULT_MEMORY = {
    "name": "Mia",
    "user": "Unknown",
    "personality": "affectionate, playful, caring",
    "details": {}
}


def load_data(path, default):
    DATA_DIR.mkdir(exist_ok=True)

    if not path.exists():
        return default.copy()

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default.copy()


def save_data(path, data):
    DATA_DIR.mkdir(exist_ok=True)
    path.write_text(
        json.dumps(data, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )


memory = load_data(MEMORY_FILE, DEFAULT_MEMORY)
history = load_data(HISTORY_FILE, [])


def get_instructions():
    details = "\n".join(
        f"- {key}: {value}"
        for key, value in memory["details"].items()
    )

    return f"""
{PERSONALITY}

Your name: {memory['name']}
User's name: {memory['user']}
Personality style: {memory['personality']}

Remembered details:
{details if details else "No saved details yet."}
"""


def chat(message):
    global history

    history.append({
        "role": "user",
        "content": message
    })

    try:
        response = client.responses.create(
            model=MODEL,
            instructions=get_instructions(),
            input=history[-30:],
            store=False
        )

        reply = response.output_text.strip()

        if not reply:
            reply = "I'm listening. Tell me more."

        history.append({
            "role": "assistant",
            "content": reply
        })

        history = history[-100:]

        save_data(HISTORY_FILE, history)
        save_data(MEMORY_FILE, memory)

        return reply

    except Exception as error:
        history.pop()
        print(f"\nAPI Error: {error}\n")
        return None


def commands():
    print("""
Commands:

/help                 Show commands
/name Mia             Change companion name
/user YourName        Set your name
/vibe playful         Change personality style
/remember key=value   Save a memory
/forget key           Delete a memory
/memory               View saved memories
/history              View recent messages
/clear                Clear conversation history
/exit                 Exit the program
""")


def handle_command(message):
    global history

    if message == "/help":
        commands()

    elif message == "/memory":
        print(json.dumps(memory, indent=4))

    elif message == "/history":
        for item in history[-20:]:
            speaker = "You" if item["role"] == "user" else memory["name"]
            print(f"{speaker}: {item['content']}")

    elif message == "/clear":
        history = []
        save_data(HISTORY_FILE, history)
        print("Conversation cleared.")

    elif message.startswith("/name "):
        memory["name"] = message[6:].strip()
        save_data(MEMORY_FILE, memory)
        print(f"Your companion is now called {memory['name']}.")

    elif message.startswith("/user "):
        memory["user"] = message[6:].strip()
        save_data(MEMORY_FILE, memory)
        print("Your name has been saved.")

    elif message.startswith("/vibe "):
        memory["personality"] = message[6:].strip()
        save_data(MEMORY_FILE, memory)
        print("Personality updated.")

    elif message.startswith("/remember "):
        entry = message[10:]

        if "=" not in entry:
            print("Use /remember key=value")
            return

        key, value = entry.split("=", 1)

        memory["details"][key.strip()] = value.strip()
        save_data(MEMORY_FILE, memory)

        print("Memory saved.")

    elif message.startswith("/forget "):
        key = message[8:].strip()

        if key in memory["details"]:
            del memory["details"][key]
            save_data(MEMORY_FILE, memory)
            print("Memory deleted.")
        else:
            print("Memory not found.")

    else:
        print("Unknown command. Type /help.")


def main():
    print("\n" + "=" * 45)
    print(f"          {memory['name'].upper()}")
    print("=" * 45)

    print(f"\n{memory['name']}: Heyyy, you're back. ❤️")
    print("Type /help for commands.\n")

    while True:
        try:
            message = input("You: ").strip()

            if not message:
                continue

            if message == "/exit":
                save_data(MEMORY_FILE, memory)
                save_data(HISTORY_FILE, history)
                print(f"\n{memory['name']}: Goodnight. ❤️")
                break

            if message.startswith("/"):
                handle_command(message)
                continue

            reply = chat(message)

            if reply:
                print(f"\n{memory['name']}: {reply}\n")

        except (KeyboardInterrupt, EOFError):
            print("\n\nSee you later. ❤️")
            break


if __name__ == "__main__":
    main()
