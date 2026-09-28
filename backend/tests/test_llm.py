"""C3: the model adapter's modes, recordings and tracing. No test touches the network: API
calls go to a fake transport, and replay tests use one that fails if it is called."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import psycopg
import pytest
from pydantic import BaseModel

from app.db.repositories import runs
from app.domain.runs import NewLLMCall
from app.llm.anthropic_client import (
    AnthropicLLMClient,
    AnthropicTransport,
    NoToolCall,
    ToolCall,
    tool_for,
)
from app.llm.client import LLMError, MissingRecording, recording_key
from app.llm.pricing import cost_gbp
from app.llm.replay import RecordingStore
from app.llm.tracing import db_tracer

RUN = "r-test"
MODEL = "claude-sonnet-5"


class Capacity(BaseModel):
    export_mw: float
    quote: str


GOOD = {"export_mw": 49.9, "quote": "49.9 MW"}
PROMPT: dict[str, Any] = {
    "schema": Capacity,
    "system": "Extract the export capacity.",
    "user": "[planning:p1:¶4] ... 49.9 MW ...",
    "purpose": "extract:planning",
    "prompt_version": "extract.v1",
    "run_id": RUN,
}


class FakeTransport:
    """Returns queued tool inputs in order and remembers every prompt it was sent."""

    def __init__(self, *outputs: dict[str, Any]) -> None:
        self.outputs = list(outputs)
        self.prompts: list[str] = []

    def call(self, *, model: str, system: str, user: str, tool: dict[str, Any]) -> ToolCall:
        self.prompts.append(user)
        return ToolCall(input=self.outputs.pop(0), input_tokens=1000, output_tokens=200)


class NoNetwork:
    def call(self, **_: Any) -> ToolCall:
        raise AssertionError("replay must not call the API")


@pytest.fixture
def traced() -> list[NewLLMCall]:
    return []


def client(
    tmp_path: Path, traced: list[NewLLMCall], transport: Any, **kw: Any
) -> AnthropicLLMClient:
    return AnthropicLLMClient(
        trace=traced.append,
        store=RecordingStore(tmp_path),
        transport=transport,
        model=MODEL,
        **kw,
    )


def key_for_prompt() -> str:
    return recording_key(
        model=MODEL,
        prompt_version="extract.v1",
        system=PROMPT["system"],
        user=PROMPT["user"],
        schema=tool_for(Capacity)["input_schema"],
    )


def test_record_writes_a_file_that_replay_then_reads(
    tmp_path: Path, traced: list[NewLLMCall]
) -> None:
    recorded = client(tmp_path, traced, FakeTransport(GOOD)).structured(**PROMPT, mode="record")
    assert recorded == Capacity(**GOOD)
    assert (tmp_path / f"{key_for_prompt()}.json").exists()

    replayed = client(tmp_path, traced, NoNetwork()).structured(**PROMPT, mode="replay")
    assert replayed == recorded
    assert [c.replayed for c in traced] == [False, True]
    # Replay reports what the call cost live.
    assert traced[1].cost_gbp == traced[0].cost_gbp > 0


def test_replay_miss_raises_without_calling_the_api(
    tmp_path: Path, traced: list[NewLLMCall]
) -> None:
    with pytest.raises(MissingRecording) as err:
        client(tmp_path, traced, NoNetwork()).structured(**PROMPT, mode="replay")
    assert err.value.purpose == "extract:planning"
    assert err.value.key == key_for_prompt()
    assert "lens record" in str(err.value)
    assert traced == []


def test_replay_is_the_default_mode(tmp_path: Path, traced: list[NewLLMCall]) -> None:
    with pytest.raises(MissingRecording):
        client(tmp_path, traced, NoNetwork(), default_mode="replay").structured(**PROMPT)


def test_replay_first_uses_a_recording_when_present(
    tmp_path: Path, traced: list[NewLLMCall]
) -> None:
    client(tmp_path, traced, FakeTransport(GOOD)).structured(**PROMPT, mode="record")
    result = client(tmp_path, traced, NoNetwork()).structured(**PROMPT, mode="replay_first")
    assert result == Capacity(**GOOD)
    assert traced[-1].replayed is True


def test_replay_first_calls_the_api_when_absent_and_does_not_record(
    tmp_path: Path, traced: list[NewLLMCall]
) -> None:
    transport = FakeTransport(GOOD)
    result = client(tmp_path, traced, transport).structured(**PROMPT, mode="replay_first")
    assert result == Capacity(**GOOD)
    assert len(transport.prompts) == 1
    assert list(tmp_path.iterdir()) == []
    assert traced[-1].replayed is False


def test_live_calls_the_api_without_recording(tmp_path: Path, traced: list[NewLLMCall]) -> None:
    client(tmp_path, traced, FakeTransport(GOOD)).structured(**PROMPT, mode="live")
    assert list(tmp_path.iterdir()) == []


def test_a_changed_prompt_misses_the_old_recording(
    tmp_path: Path, traced: list[NewLLMCall]
) -> None:
    client(tmp_path, traced, FakeTransport(GOOD)).structured(**PROMPT, mode="record")
    with pytest.raises(MissingRecording):
        client(tmp_path, traced, NoNetwork()).structured(
            **{**PROMPT, "prompt_version": "extract.v2"}, mode="replay"
        )


def test_invalid_tool_input_is_retried_once_with_the_error(
    tmp_path: Path, traced: list[NewLLMCall]
) -> None:
    transport = FakeTransport({"export_mw": "about fifty"}, GOOD)
    result = client(tmp_path, traced, transport).structured(**PROMPT, mode="record")

    assert result == Capacity(**GOOD)
    assert transport.prompts[0] == PROMPT["user"]
    assert "failed validation" in transport.prompts[1] and "export_mw" in transport.prompts[1]
    # Both attempts are paid for.
    assert (traced[0].input_tokens, traced[0].output_tokens) == (2000, 400)


def test_invalid_tool_input_twice_raises(tmp_path: Path, traced: list[NewLLMCall]) -> None:
    bad = {"export_mw": "about fifty"}
    with pytest.raises(LLMError):
        client(tmp_path, traced, FakeTransport(bad, bad)).structured(**PROMPT, mode="record")
    assert list(tmp_path.iterdir()) == []
    assert traced == []


def test_recording_keeps_caller_metadata(tmp_path: Path, traced: list[NewLLMCall]) -> None:
    client(tmp_path, traced, FakeTransport(GOOD)).structured(
        **PROMPT, mode="record", metadata={"retrieved": ["ppa:p4:¶2"]}
    )
    recording = RecordingStore(tmp_path).load(key_for_prompt())
    assert recording is not None
    assert recording.metadata == {"retrieved": ["ppa:p4:¶2"]}
    assert recording.output == GOOD


def test_recording_key_ignores_dict_order() -> None:
    a = recording_key(model="m", prompt_version="v", system="s", user="u", schema={"a": 1, "b": 2})
    b = recording_key(model="m", prompt_version="v", system="s", user="u", schema={"b": 2, "a": 1})
    assert a == b


def test_cost_uses_the_price_list() -> None:
    # 1M input at $2 + 1M output at $10 = $12, times the configured GBP rate.
    assert cost_gbp(MODEL, 1_000_000, 1_000_000) == Decimal("9.00000")
    with pytest.raises(KeyError, match=r"pricing\.py"):
        cost_gbp("claude-unknown", 1, 1)


@pytest.mark.db
def test_every_call_writes_an_llm_calls_row(tmp_path: Path, conn: psycopg.Connection) -> None:
    runs.create_run(conn, RUN, "eval", date(2026, 9, 21))
    llm = AnthropicLLMClient(
        trace=db_tracer(conn),
        store=RecordingStore(tmp_path),
        transport=FakeTransport(GOOD),
        model=MODEL,
    )
    llm.structured(**PROMPT, mode="record")
    llm.structured(**PROMPT, mode="replay")

    rows = runs.list_llm_calls(conn, RUN)
    assert [(r.purpose, r.prompt_version, r.replayed) for r in rows] == [
        ("extract:planning", "extract.v1", False),
        ("extract:planning", "extract.v1", True),
    ]
    assert {r.request_hash for r in rows} == {key_for_prompt()}


class StubMessages:
    def __init__(self, response: Any) -> None:
        self.response = response
        self.kwargs: dict[str, Any] = {}

    def create(self, **kwargs: Any) -> Any:
        self.kwargs = kwargs
        return self.response


def stub_transport(response: Any) -> tuple[AnthropicTransport, StubMessages]:
    transport = AnthropicTransport(api_key="test-key")
    messages = StubMessages(response)
    transport._client = SimpleNamespace(messages=messages)  # type: ignore[assignment]
    return transport, messages


def test_transport_forces_the_tool_and_sends_no_sampling_params() -> None:
    response = SimpleNamespace(
        stop_reason="tool_use",
        content=[
            SimpleNamespace(type="thinking"),
            SimpleNamespace(type="tool_use", input=GOOD),
        ],
        usage=SimpleNamespace(input_tokens=1200, output_tokens=80),
    )
    transport, messages = stub_transport(response)
    tool = tool_for(Capacity)

    call = transport.call(model=MODEL, system="sys", user="usr", tool=tool)

    assert call == ToolCall(input=GOOD, input_tokens=1200, output_tokens=80)
    assert messages.kwargs["tool_choice"] == {"type": "tool", "name": "Capacity"}
    assert messages.kwargs["tools"][0]["input_schema"] == Capacity.model_json_schema()
    assert messages.kwargs["messages"] == [{"role": "user", "content": "usr"}]
    assert not {"temperature", "top_p", "top_k"} & set(messages.kwargs)


def test_transport_raises_when_the_model_does_not_call_the_tool() -> None:
    response = SimpleNamespace(
        stop_reason="refusal", content=[], usage=SimpleNamespace(input_tokens=1, output_tokens=0)
    )
    transport, _ = stub_transport(response)
    with pytest.raises(LLMError, match="refusal"):
        transport.call(model=MODEL, system="s", user="u", tool=tool_for(Capacity))


def test_transport_turns_thinking_off_so_the_tool_call_is_forced() -> None:
    response = SimpleNamespace(
        stop_reason="tool_use",
        content=[SimpleNamespace(type="tool_use", input=GOOD)],
        usage=SimpleNamespace(input_tokens=10, output_tokens=5),
    )
    transport, messages = stub_transport(response)
    transport.call(model=MODEL, system="s", user="u", tool=tool_for(Capacity))
    assert messages.kwargs["thinking"] == {"type": "disabled"}


class EndsTurnOnce:
    """Ends its turn without the tool the first time, as the real model once did."""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def call(self, *, user: str, **_: Any) -> ToolCall:
        self.prompts.append(user)
        if len(self.prompts) == 1:
            raise NoToolCall("end_turn", 300, 20)
        return ToolCall(input=GOOD, input_tokens=300, output_tokens=40)


def test_a_missing_tool_call_is_retried_once(tmp_path: Path, traced: list[NewLLMCall]) -> None:
    transport = EndsTurnOnce()
    result = client(tmp_path, traced, transport).structured(**PROMPT, mode="record")
    assert result == Capacity(**GOOD)
    assert "Answer by calling Capacity." in transport.prompts[1]
    assert (traced[0].input_tokens, traced[0].output_tokens) == (600, 60)


def test_two_missing_tool_calls_raise(tmp_path: Path, traced: list[NewLLMCall]) -> None:
    class AlwaysEnds:
        def call(self, **_: Any) -> ToolCall:
            raise NoToolCall("end_turn", 1, 1)

    with pytest.raises(LLMError, match="no Capacity call, twice"):
        client(tmp_path, traced, AlwaysEnds()).structured(**PROMPT, mode="record")
