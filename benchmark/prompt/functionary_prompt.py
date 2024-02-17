import os
import re
from openai import OpenAI


class FunctionaryPrompt:

    def __init__(
        self,
        query,
        lang='en',
        upload_file_paths=[],
        model_name="meetkai/functionary-small-v2.2",
        base_url="http://0.0.0.0:8000/v1",
    ):
        self.query = query
        self.lang = lang
        self.upload_file_paths = [
            f'`{os.path.basename(fname)}`' for fname in upload_file_paths
        ]
        self.client = OpenAI(base_url=base_url, api_key="asd")
        self.model_name = model_name

    def build_messages_and_tools(self, prev_messages):
        messages = [{"role": "user", "content": self.query}] + prev_messages
        tools = [{"type": "code_interpreter"}]
        
        return messages, tools
    
    def chat_completion(self, messages, tools, tool_choice="auto", temperature=0.0, max_tokens=1024):
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature=temperature,
            max_tokens=max_tokens,
        ).choices[0].message
        
        return response
    
    def build_observation(self, observation):
        return f'\nObservation: {observation}\nThought:'
