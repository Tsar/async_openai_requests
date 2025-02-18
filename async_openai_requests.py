import json
import io
import time
from datetime import datetime
import asyncio
import aiohttp
import logging

logInfo = lambda text, logger: logger.getChild(__name__).info(text)
logDebug = lambda text, logger: logger.getChild(__name__).debug(text)

t = lambda: time.time()
ts = lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')

class StatusNot200Exception(Exception):
    def __init__(self, message, status, reason, detailsForLogging=None):
        self.message = message
        self.status = status
        self.reason = reason
        self.detailsForLogging = detailsForLogging
        self.attempts = None

    def setAttempts(self, attempts):
        self.attempts = attempts

    def __str__(self):
        attemptsText = '' if self.attempts is None else f' [made {self.attempts} attempts]'
        return f'{self.message}{attemptsText}: {self.status} {self.reason}'

class Usage:
    def __init__(self, usageObject):
        self.promptTokens = usageObject['prompt_tokens']
        self.completionTokens = usageObject['completion_tokens']
        self.totalTokens = usageObject['total_tokens']

    def __str__(self):
        return f'Usage:\n * prompt tokens: {self.promptTokens}\n * completion tokens: {self.completionTokens}\n * total tokens: {self.totalTokens}'

async def transcribe(audioData, apiKey, model='whisper-1'):
    data = aiohttp.FormData()
    data.add_field(
        name='file',
        value=io.BytesIO(audioData),
        filename='temp.webm',
    )
    data.add_field(
        name='model',
        value=model,
    )
    async with aiohttp.ClientSession() as session:
        async with session.post('https://api.openai.com/v1/audio/transcriptions', data=data, headers={'Authorization': f'Bearer {apiKey}'}) as resp:
            if resp.status != 200:
                raise StatusNot200Exception(f'Request to {model} failed', resp.status, resp.reason)
            result = await resp.json()
            return result['text']

async def requestChatCompletion(messages, gptModel, apiKey, additionalParams=None, usageCallback=None, logger=logging.getLogger("default")):
    request = {
        'model': gptModel,
        'messages': messages,
    }
    if additionalParams is not None:
        request.update(additionalParams)
    logDebug(f'Request to {gptModel}: {request}', logger)
    async with aiohttp.ClientSession() as session:
        async with session.post('https://api.openai.com/v1/chat/completions', json=request, headers={'Authorization': f'Bearer {apiKey}'}) as resp:
            if resp.status != 200:
                errorResult = None
                errorCode = None
                if resp.content_type.lower() == 'application/json':
                    errorResult = await resp.json()
                    errorCode = errorResult.get('error', {}).get('code')
                raise StatusNot200Exception(
                    message=f'Request to {gptModel} failed',
                    status=resp.status,
                    reason=resp.reason + ('' if errorCode is None else f', {errorCode}'),
                    detailsForLogging=errorResult,
                )
            result = await resp.json()
            logDebug(f'Response body from {gptModel}: {result}', logger)
            if usageCallback is not None:
                usageCallback(Usage(result['usage']))
            return result['choices'][0]['message']['content']

async def requestChatCompletionStream(messages, gptModel, apiKey, additionalParams=None, usageCallback=None, logger=logging.getLogger("default")):
    request = {
        'model': gptModel,
        'messages': messages,
        'stream': True,
    }
    if additionalParams is not None:
        request.update(additionalParams)
    if usageCallback is not None:
        request.update({'stream_options': {'include_usage': True}})
    logDebug(f'Request to {gptModel}: {request}', logger)
    async with aiohttp.ClientSession() as session:
        async with session.post('https://api.openai.com/v1/chat/completions', json=request, headers={'Authorization': f'Bearer {apiKey}'}) as resp:
            contentType = resp.content_type.lower()
            if resp.status != 200:
                errorResult = None
                errorCode = None
                if contentType == 'application/json':
                    errorResult = await resp.json()
                    errorCode = errorResult.get('error', {}).get('code')
                raise StatusNot200Exception(
                    message=f'Request to {gptModel} failed',
                    status=resp.status,
                    reason=resp.reason + ('' if errorCode is None else f', {errorCode}'),
                    detailsForLogging=errorResult,
                )
            if contentType != 'text/event-stream':
                raise RuntimeError(f'Expected content type "text/event-stream", but got "{contentType}"')
            async for line in resp.content:
                logDebug(f'Got: [{line}]', logger)
                line = line.strip()
                if line == b'':
                    continue
                elif line == b'data: [DONE]':
                    break
                elif line.startswith(b'data: '):
                    lineWithoutPrefix = line[len(b'data: '):]
                    resultPart = json.loads(lineWithoutPrefix.decode('UTF-8'))
                    if usageCallback is not None:
                        usageObject = resultPart.get('usage')
                        if usageObject is not None:
                            usageCallback(Usage(usageObject))
                    choices = resultPart.get('choices')
                    if choices is not None and len(choices) > 0:
                        resultDelta = choices[0]['delta']
                        if 'content' in resultDelta:
                            yield resultDelta['content']
                else:
                    raise RuntimeError(f'Got some garbage in stream: "{line}"')

async def retryCoroutine(coroutine, *args, maxAttempts=3, sleepBeforeRetry=0.3, logger=logging.getLogger("default"), **kwargs):
    allStartTimestamp = t()
    for attempt in range(maxAttempts):
        startTimestamp = t()
        try:
            result = await coroutine(*args, **kwargs)
            endTimestamp = t()
            elapsed = endTimestamp - startTimestamp
            allElapsed = endTimestamp - allStartTimestamp
            logInfo(f'{coroutine.__name__} completed in {elapsed:.3f}s' + (f' [all {attempt + 1} attempts took {allElapsed:.3f}s]' if attempt > 0 else ''), logger)
            return result
        except Exception as ex:
            endTimestamp = t()
            elapsed = endTimestamp - startTimestamp
            if isinstance(ex, StatusNot200Exception):
                ex.setAttempts(attempt + 1)
            if attempt == maxAttempts - 1:
                allElapsed = endTimestamp - allStartTimestamp
                logInfo(f'All {maxAttempts} attempts to call {coroutine.__name__} failed in {allElapsed:.3f}s, last error: {ex}', logger)
                raise ex
            logInfo(f'Attempt {attempt + 1} to call {coroutine.__name__} failed in {elapsed:.3f}s with error: {ex}', logger)
            await asyncio.sleep(sleepBeforeRetry)
