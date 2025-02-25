"""An image generation agent implemented by assistant"""
import json
import os
import urllib.parse

import json5

from qwen_agent.agents import Assistant
from qwen_agent.tools.base import BaseTool, register_tool


# Add a custom tool named my_image_gen：
@register_tool('my_image_gen')
class MyImageGen(BaseTool):
    description = 'AI painting (image generation) service, input text description, and return the image URL drawn based on text information.'
    parameters = [{
        'name': 'prompt',
        'type': 'string',
        'description':
        'Detailed description of the desired image content, in English',
        'required': True
    }]

    def call(self, params: str, **kwargs) -> str:
        prompt = json5.loads(params)['prompt']
        prompt = urllib.parse.quote(prompt)
        return json.dumps(
            {'image_url': f'https://image.pollinations.ai/prompt/{prompt}'},
            ensure_ascii=False)


def init_agent_service():
    # settings
    llm_cfg = {'model': 'qwen-max'}
    system = (
        'According to the user\'s request, you first draw a picture and then automatically '
        'run code to download the picture and select an image operation from the given document '
        'to process the image')

    tools = ['my_image_gen', 'code_interpreter'
             ]  # code_interpreter is a built-in tool in Qwen-Agent
    bot = Assistant(llm=llm_cfg,
                    system_message=system,
                    function_list=tools,
                    files=[os.path.abspath('resource/doc.pdf')])

    return bot


def app():
    # define the agent
    bot = init_agent_service()

    # chat
    messages = []
    while True:
        query = input('user question: ')
        messages.append({'role': 'user', 'content': query})
        response = []
        for response in bot.run(messages=messages):
            print('bot response:', response)
        messages.extend(response)


if __name__ == '__main__':
    app()
