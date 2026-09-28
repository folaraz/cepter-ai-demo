"""LLMClient backed by the Claude Messages API, with record/replay and tracing.

The model answers by calling one strict tool whose input schema is the requested Pydantic
schema, so the answer is always structured. claude-sonnet-5-5 rejects a forced
tool_choice, so the choice is "auto" and the system prompt says to call the tool. The tool
input is still validated with the schema. If it doesn't validate, or the model ends its
turn without calling the tool, the call is retried once with a note appended to the
prompt, then an LLMError is raised.

Sampling parameters are not sent: the model rejects a non-default temperature, and
repeatability comes from replaying recordings, not from temperature 0.

Thinking is "between_tools", the lowest setting on claude-sonnet-5-5 (it rejects
"disabled"): no up-front thinking, and none is needed for a single tool call.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

import anthropic
from anthropic.types import (
    MessageParam,
    ThinkingConfigBetweenToolsParam,
    ToolChoiceAutoParam,
    ToolParam,
)
from pydantic import BaseModel, ValidationError

from app.config import get_settings
from app.domain.runs import NewLLMCall
from app.llm.client import LLMError, MissingRecording, Mode, T, recording_key
from app.llm.pricing import cost_gbp
from app.llm.replay import Recording, RecordingStore

MAX_TOKENS = 16_000

Tracer = Callable[[NewLLMCall], None]


@dataclass(frozen=True)
class ToolCall:
    input: dict[str, Any]
    input_tokens: int
    output_tokens: int


class Transport(Protocol):
    """One tool call. Tests substitute a fake so they never touch the network."""

    def call(self, *, model: str, system: str, user: str, tool: dict[str, Any]) -> ToolCall: ...


class NoToolCall(LLMError):
    """The model ended its turn without calling the tool."""

    def __init__(self, stop_reason: str | None, input_tokens: int, output_tokens: int) -> None:
        self.stop_reason = stop_reason
        self.input_tokens, self.output_tokens = input_tokens, output_tokens
        super().__init__(f"model stopped with {stop_reason!r} instead of a tool call")


class AnthropicTransport:
    def __init__(self, api_key: str | None = None) -> None:
        # With no key the SDK looks for credentials itself; it only fails when a call is made.
        self._client = anthropic.Anthropic(api_key=api_key)

    def call(self, *, model: str, system: str, user: str, tool: dict[str, Any]) -> ToolCall:
        messages: list[MessageParam] = [{"role": "user", "content": user}]
        tool_param = ToolParam(
            name=tool["name"],
            description=tool["description"],
            input_schema=tool["input_schema"],
            strict=True,
        )
        response = self._client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=messages,
            tools=[tool_param],
            tool_choice=ToolChoiceAutoParam(type="auto"),
            thinking=ThinkingConfigBetweenToolsParam(type="between_tools"),
        )
        usage = (response.usage.input_tokens, response.usage.output_tokens)
        for block in response.content:
            if block.type == "tool_use":
                return ToolCall(
                    input=dict(block.input), input_tokens=usage[0], output_tokens=usage[1]
                )
        raise NoToolCall(response.stop_reason, *usage)


def tool_for(schema: type[BaseModel]) -> dict[str, Any]:
    return {
        "name": schema.__name__,
        "description": f"Submit the {schema.__name__}.",
        # The SDK's strict-mode transform: additionalProperties false, unsupported keywords
        # moved into descriptions. Pydantic still validates the full schema afterwards.
        "input_schema": anthropic.transform_schema(schema),
    }


def with_tool_instruction(system: str, tool: dict[str, Any]) -> str:
    """tool_choice can't force the call, so the prompt asks for it."""
    return f"{system}\n\nAlways answer by calling the {tool['name']} tool, exactly once."


class AnthropicLLMClient:
    def __init__(
        self,
        *,
        trace: Tracer,
        store: RecordingStore | None = None,
        transport: Transport | None = None,
        model: str | None = None,
        default_mode: Mode | None = None,
    ) -> None:
        settings = get_settings()
        self._trace = trace
        self._store = store or RecordingStore()
        self._transport = transport  # created on first API call, never in replay
        self._model = model or settings.llm_model
        self._default_mode: Mode = default_mode or settings.llm_mode

    def structured(
        self,
        *,
        schema: type[T],
        system: str,
        user: str,
        purpose: str,
        prompt_version: str,
        run_id: str,
        mode: Mode | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> T:
        mode = mode or self._default_mode
        tool = tool_for(schema)
        system = with_tool_instruction(system, tool)
        key = recording_key(
            model=self._model,
            prompt_version=prompt_version,
            system=system,
            user=user,
            schema=tool["input_schema"],
        )

        recording = self._store.load(key) if mode in ("replay", "replay_first") else None
        if mode == "replay" and recording is None:
            raise MissingRecording(purpose, key)

        replayed = recording is not None
        if recording is None:
            recording = self._call_api(
                schema, tool, system, user, key, purpose, prompt_version, metadata or {}
            )
            if mode == "record":
                self._store.save(recording)

        result = schema.model_validate(recording.output)
        self._trace(
            NewLLMCall(
                run_id=run_id,
                purpose=purpose,
                model=recording.model,
                prompt_version=prompt_version,
                request_hash=key,
                input_tokens=recording.input_tokens,
                output_tokens=recording.output_tokens,
                latency_ms=recording.latency_ms,
                cost_gbp=cost_gbp(recording.model, recording.input_tokens, recording.output_tokens),
                replayed=replayed,
            )
        )
        return result

    def _call_api(
        self,
        schema: type[BaseModel],
        tool: dict[str, Any],
        system: str,
        user: str,
        key: str,
        purpose: str,
        prompt_version: str,
        metadata: dict[str, Any],
    ) -> Recording:
        transport = self._transport = self._transport or AnthropicTransport(
            get_settings().anthropic_api_key
        )
        started = time.monotonic()
        input_tokens = output_tokens = 0
        prompt = user
        for attempt in (1, 2):
            try:
                call = transport.call(model=self._model, system=system, user=prompt, tool=tool)
            except NoToolCall as missing:
                input_tokens += missing.input_tokens
                output_tokens += missing.output_tokens
                if attempt == 2:
                    raise LLMError(f"{purpose}: no {tool['name']} call, twice") from missing
                prompt = f"{user}\n\nAnswer by calling {tool['name']}."
                continue
            input_tokens += call.input_tokens
            output_tokens += call.output_tokens
            try:
                schema.model_validate(call.input)
            except ValidationError as err:
                if attempt == 2:
                    raise LLMError(f"{purpose}: tool input failed validation twice") from err
                prompt = (
                    f"{user}\n\nYour previous {tool['name']} call failed validation:\n{err}\n"
                    f"Call {tool['name']} again with corrected input."
                )
                continue
            return Recording(
                key=key,
                purpose=purpose,
                model=self._model,
                prompt_version=prompt_version,
                output=call.input,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=round((time.monotonic() - started) * 1000),
                metadata=metadata,
            )
        raise AssertionError("unreachable")
