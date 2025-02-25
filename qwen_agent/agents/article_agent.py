from typing import Iterator, List

from qwen_agent.agents.assistant import Assistant
from qwen_agent.llm.schema import ASSISTANT, CONTENT, Message
from qwen_agent.prompts import ContinueWriting, WriteFromScratch


class ArticleAgent(Assistant):

    def _run(self,
             messages: List[Message],
             lang: str = 'en',
             max_ref_token: int = 4000,
             full_article: bool = False,
             **kwargs) -> Iterator[List[Message]]:

        # need to use Memory agent for data management
        *_, last = self.mem.run(messages=messages,
                                max_ref_token=max_ref_token,
                                **kwargs)
        _ref = last[-1][CONTENT]

        response = []
        if _ref:
            response.append(
                Message(ASSISTANT,
                        f'>\n> Search for relevant information: \n{_ref}\n'))
            yield response

        if full_article:
            writing_agent = WriteFromScratch(llm=self.llm)
        else:
            writing_agent = ContinueWriting(llm=self.llm)
            response.append(Message(ASSISTANT, '>\n> Writing Text: \n'))
            yield response
        res = writing_agent.run(messages=messages, lang=lang, knowledge=_ref)
        for trunk in res:
            yield response + trunk
