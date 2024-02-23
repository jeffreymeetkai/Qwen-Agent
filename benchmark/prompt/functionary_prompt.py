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
        self.query = query.split("<|im_end|>\n<|im_start|>")
        self.lang = lang
        self.upload_file_paths = [
            f'`{os.path.basename(fname)}`' for fname in upload_file_paths
        ]
        self.client = OpenAI(base_url=base_url, api_key="asd")
        self.model_name = model_name

    def build_messages_and_tools(self, prev_messages):
        messages = []
        for query in self.query:
            if not query.startswith("assistant\n"):
                messages.append({"role": "user", "content": query})
            else:
                query = query.replace("\nThought:", "")
                if "\nAction:" in query:
                    content = query[len("assistant\n"):query.index("\nAction:")]
                    action = query[query.index("\nAction:") + len("\nAction:"):query.index("\nAction Input:")].strip()
                    action_input = query[query.index("\nAction Input:") + len("\nAction Input:"):query.index("\nObservation:")]
                    action_input = action_input.removeprefix("\n```py\n").removesuffix("\n```")
                    observation = query[query.index("\nObservation:") + len("\nObservation:"):].strip()
                    messages.append(
                        {
                            "role": "assistant", 
                            "content": content, 
                            "tool_calls": [
                                {
                                    "type": "function", 
                                    "function": {
                                        "name": "python" if action == "code_interpreter" else action,
                                        "arguments": action_input
                                    }
                                }
                            ]
                        }
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "name": "python" if action == "code_interpreter" else action,
                            "content": observation
                        }
                    )
                else:
                    breakpoint()
        messages += prev_messages
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
