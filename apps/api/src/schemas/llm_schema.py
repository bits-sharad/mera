from pydantic import BaseModel


class PromptRequest(BaseModel):
    prompt: str


class SummarizeRequest(BaseModel):
    text: str


class FunFactRequest(BaseModel):
    topic: str
