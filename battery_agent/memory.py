from utils.exp import save_to_jsonl
from utils.llm import get_prompt_template

class BatteryAgentMemory:

    def __init__(self, memory_path: str = "./results/memory.jsonl"):
        self.memory_path = memory_path
        self.messages_memory = [{
            "role": "system",
            "content": get_prompt_template("SYSTEM_PROMPT")
        }]

    def add_messages_memory(self, messages):
        self.messages_memory.extend(messages)
        save_to_jsonl(self.messages_memory, self.memory_path, mode="w")

    def get_messages_memory(self):
        return self.messages_memory
