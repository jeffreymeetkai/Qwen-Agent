import copy
from typing import Dict, Iterator, List, Optional, Tuple, Union

from qwen_agent.agents import Assistant
from qwen_agent.llm import BaseChatModel
from qwen_agent.llm.schema import (ASSISTANT, CONTENT, DEFAULT_SYSTEM_MESSAGE,
                                   ROLE, ContentItem, Message)
from qwen_agent.utils.utils import (get_basename_from_url, has_chinese_chars,
                                    parser_function)

PROMPT_REACT = """Answer the following questions as best you can. You have access to the following tools:

{tool_descs}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can be repeated zero or more times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {query}"""


class ReActChat(Assistant):
    """
        Using ReAct format to call tools
    """

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
                 files: Optional[List[str]] = None):
        super().__init__(function_list=function_list,
                         llm=llm,
                         system_message=system_message,
                         files=files)
        stop = self.llm.generate_cfg.get('stop', [])
        fn_stop = ['Observation:', 'Observation:\n']
        self.llm.generate_cfg['stop'] = stop + [
            x for x in fn_stop if x not in stop
        ]
        assert not self.llm.model.startswith(
            'qwen-vl'), 'Now this React format does not support VL LLM'

    def _run(self,
             messages: List[Message],
             lang: str = 'en',
             **kwargs) -> Iterator[List[Message]]:

        messages = self._preprocess_react_prompt(messages)

        max_turn = 5
        response = []
        while True and max_turn > 0:
            max_turn -= 1
            output_stream = self._call_llm(messages=messages)
            output = []

            # yield the streaming response
            response_tmp = copy.deepcopy(response)
            for output in output_stream:
                if not response_tmp:
                    yield output
                else:
                    response_tmp[-1][
                        CONTENT] = response[-1][CONTENT] + output[-1][CONTENT]
                    yield response_tmp
            # record the incremental response
            assert len(output) == 1 and output[-1][ROLE] == ASSISTANT
            if not response:
                response += output
            else:
                response[-1][CONTENT] += output[-1][CONTENT]

            output = output[-1][CONTENT]

            use_tool, action, action_input, output = self._detect_tool(output)

            if use_tool:
                observation = self._call_tool(action,
                                              action_input,
                                              messages=messages)
                observation = f'\nObservation: {observation}\nThought: '
                response[-1][CONTENT] += observation
                yield response
                if isinstance(messages[-1][CONTENT], list):
                    if not ('text' in messages[-1][CONTENT][-1]
                            and messages[-1][CONTENT][-1]['text'].endswith(
                                '\nThought: ')):
                        if not output.startswith('\n'):
                            output = '\n' + output
                    messages[-1][CONTENT].append(
                        ContentItem(text=output + observation))
                else:
                    if not (messages[-1][CONTENT].endswith('\nThought: ')):
                        if not output.startswith('\n'):
                            output = '\n' + output
                    messages[-1][CONTENT] += output + observation
            else:
                break

    def _detect_tool(self, text: str) -> Tuple[bool, str, str, str]:
        special_func_token = '\nAction:'
        special_args_token = '\nAction Input:'
        special_obs_token = '\nObservation:'
        func_name, func_args = None, None
        i = text.rfind(special_func_token)
        j = text.rfind(special_args_token)
        k = text.rfind(special_obs_token)
        if 0 <= i < j:  # If the text has `Action` and `Action input`,
            if k < j:  # but does not contain `Observation`,
                # then it is likely that `Observation` is ommited by the LLM,
                # because the output text may have discarded the stop word.
                text = text.rstrip() + special_obs_token  # Add it back.
            k = text.rfind(special_obs_token)
            func_name = text[i + len(special_func_token):j].strip()
            func_args = text[j + len(special_args_token):k].strip()
            text = text[:k]  # Discard '\nObservation:'.

        return (func_name is not None), func_name, func_args, text

    def _preprocess_react_prompt(self,
                                 messages: List[Message]) -> List[Message]:
        tool_descs = '\n\n'.join(
            parser_function(func.function)
            for func in self.function_map.values())
        tool_names = ','.join(tool.name for tool in self.function_map.values())

        if isinstance(messages[-1][CONTENT], str):
            prompt = PROMPT_REACT.format(tool_descs=tool_descs,
                                         tool_names=tool_names,
                                         query=messages[-1][CONTENT])
            messages[-1][CONTENT] = prompt
            return messages
        else:
            query = ''
            new_content = []
            files = []
            for item in messages[-1][CONTENT]:
                for k, v in item.model_dump().items():
                    if k == 'text':
                        query += v
                    elif k == 'file':
                        files.append(v)
                    else:
                        new_content.append(item)
            if files:
                has_zh = has_chinese_chars(query)
                upload = []
                for f in [get_basename_from_url(f) for f in files]:
                    if has_zh:
                        upload.append(f'[文件]({f})')
                    else:
                        upload.append(f'[file]({f})')
                upload = ' '.join(upload)
                if has_zh:
                    upload = f'（上传了 {upload}）\n\n'
                else:
                    upload = f'(Uploaded {upload})\n\n'
                query = upload + query

            prompt = PROMPT_REACT.format(tool_descs=tool_descs,
                                         tool_names=tool_names,
                                         query=query)
            new_content.insert(0, ContentItem(text=prompt))
            messages[-1][CONTENT] = new_content
            return messages
