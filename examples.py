#!/usr/bin/env python3

# How to use:
# 1. Put your OpenAI API key to openai_api_key.txt.
# 2. Run this example.

import asyncio

from async_openai_requests import requestChatCompletion, requestChatCompletionStream, retryCoroutine, StatusNot200Exception

with open('openai_api_key.txt', 'r') as f:
    apiKey = f.read().strip()

usageStats = None

def saveUsage(usage):
    global usageStats
    usageStats = usage

def printUsage():
    print(usageStats)

# How to make basic chat completion request
async def chatCompletionExample():
    userPrompt = input('Input prompt for chat completion request: ')
    messages = [
        # It is possible to have only user message here (no system message)
        {'role': 'user', 'content': userPrompt},
    ]
    try:
        response = await requestChatCompletion(
            messages=messages,
            gptModel='gpt-4o',
            apiKey=apiKey,
            additionalParams={'temperature': 1.0},  # optional argument
            usageCallback=saveUsage,                # optional argument
        )
        print(response)
        printUsage()
    except StatusNot200Exception as ex:
        print(f'Request failed: {ex.status} {ex.reason}')

# How to make chat completion request and receive response by parts as soon as they are generated
async def streamChatCompletionExample():
    userPrompt = input('Input prompt for streaming chat completion request: ')
    messages = [
        {'role': 'system', 'content': 'You always answer with a lot of emojis.'},
        {'role': 'user', 'content': userPrompt},
    ]
    try:
        responseGenerator = requestChatCompletionStream(
            messages=messages,
            gptModel='gpt-4o',
            apiKey=apiKey,
            additionalParams={'temperature': 1.0},  # optional argument
            usageCallback=saveUsage,                # optional argument
        )
        async for responsePart in responseGenerator:
            print(responsePart, end='', flush=True)
        print()
        printUsage()
    except StatusNot200Exception as ex:
        print(f'Request failed: {ex.status} {ex.reason}')

# How to use retryCoroutine() and requestChatCompletion() coroutines together,
# you may try it with invalid API key to see how retries work
async def chatCompletionWithRetriesExample():
    userPrompt = input('Input prompt for chat completion request (with retries): ')
    messages = [
        {'role': 'user', 'content': userPrompt},
    ]
    try:
        response = await retryCoroutine(
            coroutine=requestChatCompletion,
            messages=messages,
            gptModel='gpt-4o',
            apiKey=apiKey,
            additionalParams={'temperature': 1.0},  # optional argument
            usageCallback=saveUsage,                # optional argument
        )
        print(response)
        printUsage()
    except StatusNot200Exception as ex:
        print(f'Request failed: {ex.status} {ex.reason}')

async def main():
    examples = [
        chatCompletionExample,
        streamChatCompletionExample,
        chatCompletionWithRetriesExample,
    ]
    for example in examples:
        await example()
        print('-' * 40)

if __name__ == '__main__':
    asyncio.run(main())
