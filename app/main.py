import argparse
import os
import sys
import json
from openai import OpenAI
import subprocess


API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-p", required=True)
    args = p.parse_args()

    if not API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

    messages = [{"role": "user", "content": args.p}]

    while True:
        chat = client.chat.completions.create(
            model="anthropic/claude-haiku-4.5",
            messages=messages,
            tools = [
                {"type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Reads and return the contents of a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "The path to the file to read"
                            }
                        },
                        "required": ["file_path"]
                    }
                }},
                {
                "type": "function",
                "function": {
                    "name": "Write",
                    "description": "Write content to a file",
                    "parameters": {
                    "type": "object",
                    "required": ["file_path", "content"],
                    "properties": {
                        "file_path": {
                        "type": "string",
                        "description": "The path of the file to write to"
                        },
                        "content": {
                        "type": "string",
                        "description": "The content to write to the file"
                        }
                    }
                    }
                }},
                {
                "type": "function",
                "function": {
                    "name": "Bash",
                    "description": "Execute a shell command",
                    "parameters": {
                    "type": "object",
                    "required": ["command"],
                    "properties": {
                        "command": {
                        "type": "string",
                        "description": "The command to execute"
                        }
                    }
                    }
                }},
            ]
        )

        if not chat.choices or len(chat.choices) == 0:
            raise RuntimeError("no choices in response")

        # You can use print statements as follows for debugging, they'll be visible when running tests.
        print("Logs from your program will appear here!", file=sys.stderr)

        first_choice = chat.choices[0]
        assistant_message = first_choice.message
        messages.append(assistant_message.model_dump())

        if not assistant_message.tool_calls:
            print(assistant_message.content)
            break

        for each_tool in assistant_message.tool_calls:
            arguments = json.loads(each_tool.function.arguments)

            if each_tool.function.name == "read_file":
                file_path = arguments["file_path"]
                with open(file_path, "r", encoding="utf-8") as file:
                    result = file.read()

            elif each_tool.function.name == "Write":
                file_path = arguments["file_path"]                
                content = arguments["content"]

                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(content)

                    result = "File written successfully"
            elif each_tool.function.name == "Bash":
                command = arguments["command"]

                completed = subprocess.run(command, shell=True, capture_output=True, text=True)

                if completed.returncode == 0:
                    result = completed.stdout or "Command completed successfully"
                else:
                    result = completed.stderr or (f"Command failed with exit code {completed.returncode}")

            messages.append({
                "role": "tool",
                "tool_call_id": each_tool.id,
                "content": result,
            })

if __name__ == "__main__":
    main()
