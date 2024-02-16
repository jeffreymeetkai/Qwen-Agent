import os
from openai import OpenAI


class FunctionaryPrompt:

    def __init__(self, query, lang='en', upload_file_paths=[]):
        self.query = query
        self.lang = lang
        self.upload_file_paths = [
            f'`{os.path.basename(fname)}`' for fname in upload_file_paths
        ]

    def build_messages_and_tools(self):
        messages = [{"role": "user", "content": self.query}]
        tools = [{"type": "code_interpreter"}]
        
        return messages, tools
    
    def chat_completion(self, messages, tools, tool_choice="auto", temperature=0.0, max_tokens=1024):
        pass
