#!/usr/bin/env python3
"""Build a runtime-backed Codex discussion smoke directory through the wrapper.

This is intentionally not a full subagent smoke. It simulates the Codex
spawn/wait boundary, then requires every discussion artifact after that boundary
to be produced through runtime commands.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
WRAPPER = REPO / "plugins/codex/runtime/swarm_runtime_wrapper.py"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def run_wrapper(*args: str, expect_ok: bool = True) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, str(WRAPPER), *args],
        cwd=str(REPO),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"wrapper output was not JSON for {args}: {exc}\nstdout={completed.stdout}\nstderr={completed.stderr}"
        ) from exc

    if expect_ok and completed.returncode != 0:
        raise AssertionError(f"wrapper command failed: {args}\n{completed.stdout}\n{completed.stderr}")
    if not expect_ok and completed.returncode == 0:
        raise AssertionError(f"wrapper command unexpectedly passed: {args}\n{completed.stdout}")
    return payload


def persona(persona_id: str, name: str, bias: str) -> dict[str, Any]:
    return {
        "id": persona_id,
        "name": name,
        "expertise": ["runtime architecture", "agent orchestration"],
        "thinkingStyle": "artifact-first",
        "bias": bias,
        "replyTendency": "state a concrete implementation risk",
        "stakes": "keep the parent thread thin",
        "blindSpots": ["overfitting to fixture-only evidence"],
    }


def build_flow(root: Path) -> dict[str, Any]:
    discussion_id = "runtime-flow-smoke"
    discussion = root / ".swarm" / "discussions" / discussion_id
    tmp = discussion / "tmp"
    artifacts = discussion / "artifacts"
    personas = [
        persona("architect", "architect", "prefer runtime-owned protocol state"),
        persona("contrarian", "contrarian", "prefer proving failure behavior before defaulting"),
    ]
    discussion.mkdir(parents=True)
    tmp.mkdir(parents=True)
    artifacts.mkdir(parents=True)

    write_json(
        discussion / "manifest.json",
        {
            "schemaVersion": 2,
            "id": discussion_id,
            "title": "Runtime flow smoke",
            "mode": "lightweight",
            "status": "running",
            "personas": personas,
        },
    )

    brief_path = tmp / "brief.json"
    write_json(
        brief_path,
        {
            "topic": "Can the Codex skill run a runtime-backed discussion flow?",
            "objective": "Prove prompt-build, transport fan-in, and WAL commands compose into one discussion artifact tree.",
            "mode": "lightweight",
            "discussionId": discussion_id,
            "parentContext": "This is a conformance smoke; host spawn/wait is simulated, runtime mechanics are real.",
            "constraints": [
                "Do not hand-mint message ids.",
                "Do not hand-write standard transport artifacts.",
                "Keep the parent context surface thin.",
            ],
            "knownFacts": [
                "The Codex host returns agent_id values.",
                "wait_agent may return partial completion batches.",
            ],
            "successCriteria": [
                "context-build writes context/summary.md.",
                "prompt-build writes one prompt artifact per persona.",
                "transport-collect first fails on partial fan-in, then succeeds after the second batch.",
                "append-message, checkpoint, and finalize-round produce a valid committed round.",
                "adapter-smoke and validate-loop pass on the resulting artifact tree.",
            ],
        },
    )
    context_path = discussion / "context" / "summary.md"
    context = run_wrapper("context-build", "--brief", str(brief_path), "--out", str(context_path))
    assert context["result"]["ok"] is True
    assert context_path.exists()

    prompt_outputs: list[Path] = []
    for entry in personas:
        request_path = discussion / "prompts" / "r001" / "declaration" / entry["id"] / "request.json"
        out_dir = request_path.parent
        write_json(
            request_path,
            {
                "phase": "declaration",
                "roundId": 1,
                "topic": "Can the Codex skill run a runtime-backed discussion flow?",
                "contextSummaryPath": str(context_path),
                "persona": entry,
                "messages": [],
                "visibilityBudget": 100000,
                "instruction": "Declare whether the runtime-backed path is ready to be the default smoke surface.",
            },
        )
        prompt = run_wrapper("prompt-build", "--request", str(request_path), "--out-dir", str(out_dir))
        assert prompt["result"]["ok"] is True
        prompt_outputs.append(out_dir / "prompt-build.json")
        assert (out_dir / "prompt.txt").exists()

    spawn_order_path = tmp / "spawn-order-r001-declaration.json"
    write_json(
        spawn_order_path,
        [
            {"agentId": "agent-architect", "persona": "architect"},
            {"agentId": "agent-contrarian", "persona": "contrarian"},
        ],
    )
    transport_init = run_wrapper(
        "transport-init",
        "--dir",
        str(discussion),
        "--host",
        "codex",
        "--discussion-id",
        discussion_id,
        "--round",
        "1",
        "--phase",
        "declaration",
        "--spawn-order",
        str(spawn_order_path),
    )
    assert transport_init["result"]["ok"] is True

    first_batch_path = tmp / "wait-batch-r001-declaration-1.json"
    write_json(
        first_batch_path,
        {
            "status": {
                "agent-architect": {
                    "completed": json.dumps(
                        {
                            "name": "architect",
                            "position": "Make runtime-backed flow the default smoke path.",
                            "summary": "Prompt, fan-in, and WAL artifacts now compose through runtime commands.",
                        }
                    )
                }
            },
            "timed_out": False,
        },
    )
    run_wrapper(
        "transport-append-batch",
        "--dir",
        str(discussion),
        "--round",
        "1",
        "--phase",
        "declaration",
        "--wait-result",
        str(first_batch_path),
    )
    partial_collect = run_wrapper(
        "transport-collect",
        "--dir",
        str(discussion),
        "--round",
        "1",
        "--phase",
        "declaration",
        expect_ok=False,
    )
    assert partial_collect["result"]["result"]["complete"] is False
    assert partial_collect["result"]["result"]["missingAgentIds"] == ["agent-contrarian"]

    second_batch_path = tmp / "wait-batch-r001-declaration-2.json"
    write_json(
        second_batch_path,
        {
            "status": {
                "agent-contrarian": {
                    "completed": json.dumps(
                        {
                            "name": "contrarian",
                            "position": "Default only after the flow has an end-to-end smoke.",
                            "summary": "A helper-only smoke can miss orchestration drift.",
                        }
                    )
                }
            },
            "timed_out": False,
        },
    )
    run_wrapper(
        "transport-append-batch",
        "--dir",
        str(discussion),
        "--round",
        "1",
        "--phase",
        "declaration",
        "--wait-result",
        str(second_batch_path),
    )
    collect = run_wrapper(
        "transport-collect",
        "--dir",
        str(discussion),
        "--round",
        "1",
        "--phase",
        "declaration",
    )
    assert collect["result"]["result"]["complete"] is True
    collected_results = collect["result"]["result"]["results"]

    messages = []
    for item in collected_results:
        message_path = tmp / f"message-{item['persona']}.json"
        write_json(
            message_path,
            {
                "from": item["persona"],
                "type": "position_declaration",
                "content": item["result"],
                "references": [],
            },
        )
        append = run_wrapper(
            "append-message",
            "--dir",
            str(discussion),
            "--round",
            "1",
            "--phase",
            "declaration",
            "--message",
            str(message_path),
        )
        assert append["result"]["ok"] is True
        messages.append(append["result"]["message"])

    partial_state_path = discussion / "rounds" / "001.json.partial"
    state = json.loads(partial_state_path.read_text())
    state.update(
        {
            "topic": "Can the Codex skill run a runtime-backed discussion flow?",
            "mode": "lightweight",
            "timestamp": "2026-06-10T00:00:00Z",
            "synthesis": {
                "recommendation": "Use the runtime-backed path as the default smoke surface before live subagent rollout.",
                "qualityScore": 0.9,
            },
            "metadata": {
                "messageCount": len(state["messages"]),
                "participants": sorted({message["from"] for message in state["messages"]}),
                "referenceCount": len(state["argumentGraph"]),
            },
        }
    )
    checkpoint_state_path = tmp / "checkpoint-state-r001.json"
    write_json(checkpoint_state_path, state)
    checkpoint = run_wrapper(
        "checkpoint",
        "--dir",
        str(discussion),
        "--round",
        "1",
        "--phase",
        "synthesis",
        "--state",
        str(checkpoint_state_path),
    )
    assert checkpoint["result"]["ok"] is True

    final_state_path = tmp / "final-state-r001.json"
    write_json(final_state_path, state)
    finalize = run_wrapper(
        "finalize-round",
        "--dir",
        str(discussion),
        "--round",
        "1",
        "--state",
        str(final_state_path),
    )
    assert finalize["result"]["ok"] is True

    write_json(
        discussion / "manifest.json",
        {
            "schemaVersion": 2,
            "id": discussion_id,
            "title": "Runtime flow smoke",
            "mode": "lightweight",
            "status": "completed",
            "personas": personas,
        },
    )
    (artifacts / "synthesis.md").write_text(
        "# Synthesis\n\nUse the runtime-backed path as the default smoke surface before live subagent rollout.\n"
    )
    shutil.rmtree(tmp)

    validate_round = run_wrapper("validate-round", str(discussion / "rounds" / "001.json"))
    assert validate_round["result"]["ok"] is True

    trace = run_wrapper("trace", "--dir", str(discussion))
    assert trace["result"]["health"] == "on-track"
    write_json(artifacts / "trace.json", trace["result"])
    evidence = run_wrapper("evidence", "--dir", str(discussion), "--output", str(artifacts / "evidence.json"))
    assert evidence["result"]["outcome"]["result"] == "completed"

    adapter_smoke = run_wrapper("adapter-smoke", "--dir", str(discussion))
    assert adapter_smoke["result"]["ok"] is True
    validate_loop = run_wrapper("validate-loop", str(discussion))
    assert validate_loop["result"]["ok"] is True

    return {
        "ok": True,
        "discussionDir": str(discussion),
        "summary": {
            "contextSummary": str(context_path),
            "promptBuildCount": len(prompt_outputs),
            "partialMissingAgentIds": partial_collect["result"]["result"]["missingAgentIds"],
            "collectComplete": collect["result"]["result"]["complete"],
            "messageIds": [message["id"] for message in messages],
            "checkpointPath": checkpoint["result"]["path"],
            "finalRound": finalize["result"]["path"],
            "adapterSmokeOk": adapter_smoke["result"]["ok"],
            "validateLoopOk": validate_loop["result"]["ok"],
            "health": trace["result"]["health"],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a Codex runtime-backed discussion flow smoke")
    parser.add_argument("--keep", action="store_true", help="Keep the generated smoke directory")
    parser.add_argument("--root", type=Path, help="Root directory for the generated .swarm tree")
    args = parser.parse_args(argv)

    if args.root:
        root = args.root
        root.mkdir(parents=True, exist_ok=True)
        payload = build_flow(root)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    with tempfile.TemporaryDirectory(prefix="swarm-runtime-flow-smoke.") as tmp:
        root = Path(tmp)
        payload = build_flow(root)
        if args.keep:
            kept = Path(tempfile.mkdtemp(prefix="swarm-runtime-flow-smoke-kept."))
            shutil.copytree(root, kept, dirs_exist_ok=True)
            payload["keptRoot"] = str(kept)
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
