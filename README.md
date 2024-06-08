# Async OpenAI Requests

This is a simple module for making requests to OpenAI (ChatGPT) in asynchronous manner using coroutines.

## Example

This code will print respone to question "How to build a house?" by parts as soon as they are generated:

```python
import asyncio
from async_openai_requests import requestChatCompletionStream

API_KEY = '<put your OpenAI API key here>'

async def main():
    messages = [{'role': 'user', 'content': 'How to build a house?'}]
    responseGenerator = requestChatCompletionStream(messages=messages, gptModel='gpt-4o', apiKey=API_KEY)
    async for responsePart in responseGenerator:
        print(responsePart, end='', flush=True)
    print()

if __name__ == '__main__':
    asyncio.run(main())
```
See more examples in [example.py](https://github.com/Tsar/async_openai_requests/blob/master/example.py).

## Features

Following requests are supported:
* chat completion;
* chat completion with response streaming;
* transcribe (voice-to-text).

There is also function `retryCoroutine()` for launching a request with retries.

## Dependencies

* `asyncio`
* `aiohttp`

There is **no** dependency to official `openai` module!
