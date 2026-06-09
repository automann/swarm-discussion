#!/usr/bin/env python3
"""Two-phase harness for a live Codex runtime-backed swarm discussion smoke.

The script cannot call Codex's in-thread multi-agent tools. Instead it makes
the host boundary explicit:

1. prepare: build context and persona prompt artifacts through the runtime.
2. operator: spawn real swarm-expert agents and save raw wait_agent batches.
3. finish: feed those raw host results back through runtime transport/WAL gates.
"""

from __future__ import annotations

import argparse
import json
import shlex
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
WRAPPER = REPO / "plugins/codex/runtime/swarm_runtime_wrapper.py"
DEFAULT_DISCUSSION_ID = "live-runtime-flow"
DEFAULT_PHASE = "declaration"
DEFAULT_ROUND = 1


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def discussion_from_args(root: Path | None, discussion_dir: Path | None, discussion_id: str) -> Path:
    if discussion_dir:
        return discussion_dir.expanduser().resolve()
    if root:
        base = root.expanduser().resolve()
    else:
        base = Path(tempfile.mkdtemp(prefix="swarm-live-runtime-flow."))
    return base / ".swarm" / "discussions" / discussion_id


def run_wrapper(wrapper: Path, *args: str, expect_ok: bool | None = True) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, str(wrapper), *args],
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

    payload["_returncode"] = completed.returncode
    payload["_stderr"] = completed.stderr.strip()
    if expect_ok is True and completed.returncode != 0:
        raise AssertionError(f"wrapper command failed: {args}\n{completed.stdout}\n{completed.stderr}")
    if expect_ok is False and completed.returncode == 0:
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


def default_personas() -> list[dict[str, Any]]:
    return [
        persona("architect", "architect", "prefer runtime-owned protocol state"),
        persona("contrarian", "contrarian", "prefer proving failure behavior before defaulting"),
    ]


def quoted_command(parts: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in parts)


def write_operator_readme(
    path: Path,
    packet_path: Path,
    spawn_order_path: Path,
    first_wait_path: Path,
    finish_command: str,
) -> None:
    path.write_text(
        "\n".join(
            [
                "# Live Runtime Flow Operator Packet",
                "",
                "Use this packet from a Codex root thread that exposes `multi_agent_v1`.",
                "",
                "1. For each persona in `live-runtime-flow-packet.json`, spawn `agent_type=\"swarm-expert\"` with the listed `prompt.txt` verbatim.",
                "2. Save the returned agent IDs to `spawn-order.json` as `[ {\"agentId\": \"...\", \"persona\": \"...\"} ]`.",
                "3. Save each raw `wait_agent` response as `wait-batch-N.json`. Do not edit the raw status payload.",
                "4. Run the finish command after adding one `--wait-result` argument per saved wait batch.",
                "",
                "Packet:",
                f"- `{packet_path}`",
                "",
                "Spawn order template:",
                f"- `{spawn_order_path}`",
                "",
                "First wait batch template:",
                f"- `{first_wait_path}`",
                "",
                "Finish command:",
                "",
                "```sh",
                finish_command,
                "```",
                "",
            ]
        )
    )


def prepare_live_flow(
    discussion: Path,
    wrapper: Path,
    discussion_id: str,
    round_id: int,
    phase: str,
    clean: bool = False,
) -> dict[str, Any]:
    if discussion.exists() and clean:
        shutil.rmtree(discussion)
    if discussion.exists() and any(discussion.iterdir()):
        raise AssertionError(f"discussion directory already exists; pass --clean to replace it: {discussion}")

    operator_dir = discussion / "operator"
    context_path = discussion / "context" / "summary.md"
    prompts_root = discussion / "prompts" / f"r{round_id:03d}" / phase
    personas = default_personas()
    discussion.mkdir(parents=True, exist_ok=True)
    operator_dir.mkdir(parents=True, exist_ok=True)

    write_json(
        discussion / "manifest.json",
        {
            "schemaVersion": 2,
            "id": discussion_id,
            "title": "Live runtime flow smoke",
            "mode": "lightweight",
            "status": "running",
            "personas": personas,
        },
    )

    brief_path = operator_dir / "brief.json"
    write_json(
        brief_path,
        {
            "topic": "Can the Codex skill run a runtime-backed discussion flow with real swarm-expert agents?",
            "objective": (
                "Prove runtime prompt-build, runtime transport fan-in, and runtime WAL commands compose "
                "around real Codex subagent spawn/wait results."
            ),
            "mode": "lightweight",
            "discussionId": discussion_id,
            "parentContext": (
                "This is a live smoke for the Codex plugin path. The operator will spawn real swarm-expert "
                "agents, but all standard discussion artifacts after the host boundary must be runtime-owned."
            ),
            "constraints": [
                "Do not hand-mint message ids.",
                "Do not hand-write standard transport artifacts.",
                "Keep the parent context surface thin.",
                "Preserve raw wait_agent batches without editing their status payloads.",
            ],
            "knownFacts": [
                "The Codex host returns agent_id values.",
                "wait_agent may return partial completion batches even when timed_out is false.",
            ],
            "successCriteria": [
                "context-build writes context/summary.md.",
                "prompt-build writes one prompt artifact per persona.",
                "transport-collect succeeds only after all required agent IDs are present.",
                "append-message, checkpoint, and finalize-round produce a valid committed round.",
                "adapter-smoke and validate-loop pass on the resulting artifact tree.",
            ],
        },
    )
    context = run_wrapper(wrapper, "context-build", "--brief", str(brief_path), "--out", str(context_path))
    assert context["result"]["ok"] is True

    prompt_records: list[dict[str, Any]] = []
    for entry in personas:
        out_dir = prompts_root / entry["id"]
        request_path = out_dir / "request.json"
        write_json(
            request_path,
            {
                "phase": phase,
                "roundId": round_id,
                "topic": "Can the Codex skill run a runtime-backed discussion flow with real swarm-expert agents?",
                "contextSummaryPath": str(context_path),
                "persona": entry,
                "messages": [],
                "visibilityBudget": 100000,
                "instruction": (
                    "Declare whether the runtime-backed Codex path is ready to be the default live smoke surface. "
                    "Return one JSON object with name, position, summary, and risk."
                ),
            },
        )
        prompt = run_wrapper(wrapper, "prompt-build", "--request", str(request_path), "--out-dir", str(out_dir))
        assert prompt["result"]["ok"] is True
        prompt_records.append(
            {
                "persona": entry["id"],
                "agentType": "swarm-expert",
                "requestPath": str(request_path),
                "promptPath": str(out_dir / "prompt.txt"),
                "promptBuildPath": str(out_dir / "prompt-build.json"),
            }
        )

    spawn_order_path = operator_dir / "spawn-order.json"
    wait_batch_path = operator_dir / "wait-batch-1.json"
    write_json(spawn_order_path, [{"agentId": "<returned agent_id>", "persona": item["id"]} for item in personas])
    write_json(wait_batch_path, {"status": {"<returned agent_id>": {"completed": "<raw completed payload>"}}, "timed_out": False})

    finish_command = quoted_command(
        [
            "python3",
            str(Path(__file__).resolve()),
            "finish",
            "--discussion-dir",
            str(discussion),
            "--spawn-order",
            str(spawn_order_path),
            "--wait-result",
            str(wait_batch_path),
        ]
    )
    packet_path = operator_dir / "live-runtime-flow-packet.json"
    packet = {
        "ok": True,
        "discussionId": discussion_id,
        "discussionDir": str(discussion),
        "round": round_id,
        "phase": phase,
        "wrapper": str(wrapper),
        "contextSummary": str(context_path),
        "prompts": prompt_records,
        "spawnOrderPath": str(spawn_order_path),
        "waitBatchTemplatePath": str(wait_batch_path),
        "finishCommand": finish_command,
    }
    write_json(packet_path, packet)
    write_operator_readme(operator_dir / "README.md", packet_path, spawn_order_path, wait_batch_path, finish_command)

    return {
        "ok": True,
        "discussionDir": str(discussion),
        "operatorPacket": str(packet_path),
        "operatorReadme": str(operator_dir / "README.md"),
        "summary": {
            "contextSummary": str(context_path),
            "promptBuildCount": len(prompt_records),
            "promptPaths": [record["promptPath"] for record in prompt_records],
            "finishCommand": finish_command,
        },
    }


def content_summary(value: Any) -> str:
    if not isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    for key in ("summary", "position", "claim", "risk"):
        found = value.get(key)
        if isinstance(found, str) and found.strip():
            return found.strip()
    return json.dumps(value, sort_keys=True)


def write_message_payload(path: Path, persona_id: str, result: Any) -> None:
    write_json(
        path,
        {
            "from": persona_id,
            "type": "position_declaration",
            "content": result,
            "references": [],
        },
    )


def finish_live_flow(
    discussion: Path,
    wrapper: Path,
    spawn_order_path: Path,
    wait_result_paths: list[Path],
    round_id: int,
    phase: str,
    require_partial: bool = False,
    keep_tmp: bool = False,
    reset_transport: bool = False,
) -> dict[str, Any]:
    if not discussion.exists():
        raise AssertionError(f"discussion directory does not exist: {discussion}")
    if not spawn_order_path.exists():
        raise AssertionError(f"spawn-order file does not exist: {spawn_order_path}")
    missing_wait = [str(path) for path in wait_result_paths if not path.exists()]
    if missing_wait:
        raise AssertionError(f"wait-result file does not exist: {missing_wait[0]}")

    manifest = load_json(discussion / "manifest.json")
    discussion_id = manifest.get("id") or discussion.name
    topic = "Can the Codex skill run a runtime-backed discussion flow with real swarm-expert agents?"
    if reset_transport:
        shutil.rmtree(discussion / "transport" / f"r{round_id:03d}" / phase, ignore_errors=True)

    transport_init = run_wrapper(
        wrapper,
        "transport-init",
        "--dir",
        str(discussion),
        "--host",
        "codex",
        "--discussion-id",
        str(discussion_id),
        "--round",
        str(round_id),
        "--phase",
        phase,
        "--spawn-order",
        str(spawn_order_path),
    )
    assert transport_init["result"]["ok"] is True

    collect_attempts: list[dict[str, Any]] = []
    partial_missing: list[list[str]] = []
    for wait_result in wait_result_paths:
        appended = run_wrapper(
            wrapper,
            "transport-append-batch",
            "--dir",
            str(discussion),
            "--round",
            str(round_id),
            "--phase",
            phase,
            "--wait-result",
            str(wait_result),
        )
        assert appended["result"]["ok"] is True
        collect = run_wrapper(
            wrapper,
            "transport-collect",
            "--dir",
            str(discussion),
            "--round",
            str(round_id),
            "--phase",
            phase,
            expect_ok=None,
        )
        result = collect.get("result", {}).get("result") if isinstance(collect.get("result"), dict) else None
        if isinstance(result, dict) and result.get("complete") is False:
            partial_missing.append(result.get("missingAgentIds") or [])
        collect_attempts.append(
            {
                "waitResult": str(wait_result),
                "returncode": collect["_returncode"],
                "ok": collect.get("ok"),
                "complete": result.get("complete") if isinstance(result, dict) else None,
                "missingAgentIds": result.get("missingAgentIds") if isinstance(result, dict) else None,
            }
        )

    if require_partial and not partial_missing:
        raise AssertionError("expected at least one partial transport-collect attempt, but all attempts completed")
    final_collect = run_wrapper(
        wrapper,
        "transport-collect",
        "--dir",
        str(discussion),
        "--round",
        str(round_id),
        "--phase",
        phase,
    )
    collected = final_collect["result"]["result"]
    assert collected["complete"] is True
    collected_results = collected["results"]

    tmp = discussion / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    messages: list[dict[str, Any]] = []
    for item in collected_results:
        message_path = tmp / f"message-{item['persona']}.json"
        write_message_payload(message_path, item["persona"], item["result"])
        appended = run_wrapper(
            wrapper,
            "append-message",
            "--dir",
            str(discussion),
            "--round",
            str(round_id),
            "--phase",
            phase,
            "--message",
            str(message_path),
        )
        assert appended["result"]["ok"] is True
        messages.append(appended["result"]["message"])

    partial_state_path = discussion / "rounds" / f"{round_id:03d}.json.partial"
    state = load_json(partial_state_path)
    recommendation = "Runtime-backed live smoke completed through real Codex subagent results."
    state.update(
        {
            "topic": topic,
            "mode": manifest.get("mode") or "lightweight",
            "timestamp": utc_now(),
            "synthesis": {
                "recommendation": recommendation,
                "qualityScore": 0.9,
            },
            "metadata": {
                "messageCount": len(state["messages"]),
                "participants": sorted({message["from"] for message in state["messages"]}),
                "referenceCount": len(state["argumentGraph"]),
            },
        }
    )

    checkpoint_state_path = tmp / f"checkpoint-state-r{round_id:03d}.json"
    final_state_path = tmp / f"final-state-r{round_id:03d}.json"
    write_json(checkpoint_state_path, state)
    checkpoint = run_wrapper(
        wrapper,
        "checkpoint",
        "--dir",
        str(discussion),
        "--round",
        str(round_id),
        "--phase",
        "synthesis",
        "--state",
        str(checkpoint_state_path),
    )
    assert checkpoint["result"]["ok"] is True

    write_json(final_state_path, state)
    finalize = run_wrapper(
        wrapper,
        "finalize-round",
        "--dir",
        str(discussion),
        "--round",
        str(round_id),
        "--state",
        str(final_state_path),
    )
    assert finalize["result"]["ok"] is True

    manifest["status"] = "completed"
    write_json(discussion / "manifest.json", manifest)

    artifacts = discussion / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    synthesis_lines = ["# Synthesis", "", recommendation, ""]
    for item in collected_results:
        synthesis_lines.append(f"- {item['persona']}: {content_summary(item['result'])}")
    synthesis_lines.append("")
    (artifacts / "synthesis.md").write_text("\n".join(synthesis_lines))

    if tmp.exists() and not keep_tmp:
        shutil.rmtree(tmp)

    validate_round = run_wrapper(wrapper, "validate-round", str(discussion / "rounds" / f"{round_id:03d}.json"))
    assert validate_round["result"]["ok"] is True

    trace = run_wrapper(wrapper, "trace", "--dir", str(discussion))
    assert trace["result"]["health"] == "on-track"
    write_json(artifacts / "trace.json", trace["result"])
    evidence = run_wrapper(wrapper, "evidence", "--dir", str(discussion), "--output", str(artifacts / "evidence.json"))
    assert evidence["result"]["outcome"]["result"] == "completed"

    adapter_smoke = run_wrapper(wrapper, "adapter-smoke", "--dir", str(discussion))
    assert adapter_smoke["result"]["ok"] is True
    validate_loop = run_wrapper(wrapper, "validate-loop", str(discussion))
    assert validate_loop["result"]["ok"] is True

    return {
        "ok": True,
        "discussionDir": str(discussion),
        "summary": {
            "waitBatchCount": len(wait_result_paths),
            "collectAttempts": collect_attempts,
            "partialMissingAgentIds": partial_missing,
            "collectResultCount": 1,
            "messageIds": [message["id"] for message in messages],
            "checkpointPath": checkpoint["result"]["path"],
            "finalRound": finalize["result"]["path"],
            "traceHealth": trace["result"]["health"],
            "evidenceOutcome": evidence["result"]["outcome"]["result"],
            "adapterSmokeOk": adapter_smoke["result"]["ok"],
            "validateLoopOk": validate_loop["result"]["ok"],
        },
    }


def write_simulated_operator_inputs(
    discussion: Path,
    complete: bool,
    partial_first: bool = True,
) -> tuple[Path, list[Path]]:
    operator = discussion / "operator"
    spawn_order = operator / "spawn-order.json"
    write_json(
        spawn_order,
        [
            {"agentId": "agent-architect", "persona": "architect"},
            {"agentId": "agent-contrarian", "persona": "contrarian"},
        ],
    )
    first = operator / "wait-batch-1.json"
    if partial_first:
        write_json(
            first,
            {
                "status": {
                    "agent-architect": {
                        "completed": json.dumps(
                            {
                                "name": "architect",
                                "position": "Use runtime-backed live smoke as the default proof path.",
                                "summary": "Prompt, transport, and WAL artifacts are runtime-owned.",
                                "risk": "Operator steps still need a tight packet.",
                            }
                        )
                    }
                },
                "timed_out": False,
            },
        )
    else:
        write_json(
            first,
            {
                "status": {
                    "agent-architect": {"completed": json.dumps({"name": "architect", "summary": "Ready."})},
                    "agent-contrarian": {"completed": json.dumps({"name": "contrarian", "summary": "Probe it."})},
                },
                "timed_out": False,
            },
        )
    if not complete:
        return spawn_order, [first]

    second = operator / "wait-batch-2.json"
    write_json(
        second,
        {
            "status": {
                "agent-contrarian": {
                    "completed": json.dumps(
                        {
                            "name": "contrarian",
                            "position": "Keep the default gated by a reproducible live smoke.",
                            "summary": "A deterministic smoke is not enough without a real host-boundary run.",
                            "risk": "A stale operator transcript can hide orchestration drift.",
                        }
                    )
                }
            },
            "timed_out": False,
        },
    )
    return spawn_order, [first, second]


def run_self_test(wrapper: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="swarm-live-harness-missing.") as tmp:
        discussion = discussion_from_args(Path(tmp), None, "missing-spawn")
        prepare_live_flow(discussion, wrapper, "missing-spawn", DEFAULT_ROUND, DEFAULT_PHASE)
        missing_spawn = discussion / "operator" / "missing-spawn-order.json"
        _, waits = write_simulated_operator_inputs(discussion, complete=True)
        try:
            finish_live_flow(discussion, wrapper, missing_spawn, waits, DEFAULT_ROUND, DEFAULT_PHASE)
        except AssertionError as exc:
            checks.append({"name": "missing spawn-order fails", "ok": "spawn-order file does not exist" in str(exc)})
        else:
            checks.append({"name": "missing spawn-order fails", "ok": False})

    with tempfile.TemporaryDirectory(prefix="swarm-live-harness-partial.") as tmp:
        discussion = discussion_from_args(Path(tmp), None, "partial-fanin")
        prepare_live_flow(discussion, wrapper, "partial-fanin", DEFAULT_ROUND, DEFAULT_PHASE)
        spawn_order, waits = write_simulated_operator_inputs(discussion, complete=False)
        try:
            finish_live_flow(discussion, wrapper, spawn_order, waits, DEFAULT_ROUND, DEFAULT_PHASE)
        except AssertionError:
            collect_result = load_json(discussion / "transport" / "r001" / DEFAULT_PHASE / "collect-result.json")
            checks.append(
                {
                    "name": "partial fan-in fails before WAL",
                    "ok": collect_result["missingAgentIds"] == ["agent-contrarian"],
                }
            )
        else:
            checks.append({"name": "partial fan-in fails before WAL", "ok": False})

    with tempfile.TemporaryDirectory(prefix="swarm-live-harness-success.") as tmp:
        discussion = discussion_from_args(Path(tmp), None, "success")
        prep = prepare_live_flow(discussion, wrapper, "success", DEFAULT_ROUND, DEFAULT_PHASE)
        spawn_order, waits = write_simulated_operator_inputs(discussion, complete=True)
        finished = finish_live_flow(
            discussion,
            wrapper,
            spawn_order,
            waits,
            DEFAULT_ROUND,
            DEFAULT_PHASE,
            require_partial=True,
        )
        checks.extend(
            [
                {"name": "prepare writes two prompt artifacts", "ok": prep["summary"]["promptBuildCount"] == 2},
                {"name": "finish records partial collect attempt", "ok": bool(finished["summary"]["partialMissingAgentIds"])},
                {"name": "finish mints WAL message ids", "ok": finished["summary"]["messageIds"] == ["r1-msg-001", "r1-msg-002"]},
                {"name": "finish validates completed loop", "ok": finished["summary"]["validateLoopOk"] is True},
            ]
        )

    return {"ok": all(item["ok"] for item in checks), "checks": checks}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare or finish a live runtime-backed Codex smoke")
    parser.add_argument("--wrapper", type=Path, default=WRAPPER, help="Path to swarm_runtime_wrapper.py")
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare", help="Create prompts and an operator packet for a live smoke")
    target = prepare.add_mutually_exclusive_group()
    target.add_argument("--root", type=Path, help="Root directory where .swarm/discussions/<id> will be created")
    target.add_argument("--discussion-dir", type=Path, help="Exact discussion directory to create")
    prepare.add_argument("--discussion-id", default=DEFAULT_DISCUSSION_ID)
    prepare.add_argument("--round", type=int, default=DEFAULT_ROUND)
    prepare.add_argument("--phase", default=DEFAULT_PHASE)
    prepare.add_argument("--clean", action="store_true", help="Replace an existing discussion directory")

    finish = sub.add_parser("finish", help="Complete WAL and validation from real wait_agent batches")
    finish.add_argument("--discussion-dir", type=Path, required=True)
    finish.add_argument("--spawn-order", type=Path, required=True)
    finish.add_argument("--wait-result", type=Path, action="append", required=True)
    finish.add_argument("--round", type=int, default=DEFAULT_ROUND)
    finish.add_argument("--phase", default=DEFAULT_PHASE)
    finish.add_argument("--require-partial", action="store_true", help="Require at least one incomplete collect attempt")
    finish.add_argument("--keep-tmp", action="store_true", help="Keep tmp/ payload files after a successful finish")
    finish.add_argument("--reset-transport", action="store_true", help="Clear this round/phase transport directory first")

    sub.add_parser("self-test", help="Run deterministic failure and success checks for this harness")

    args = parser.parse_args(argv)
    wrapper = args.wrapper.expanduser().resolve()
    if not wrapper.exists():
        raise SystemExit(f"wrapper does not exist: {wrapper}")

    if args.command == "prepare":
        discussion = discussion_from_args(args.root, args.discussion_dir, args.discussion_id)
        payload = prepare_live_flow(discussion, wrapper, args.discussion_id, args.round, args.phase, clean=args.clean)
    elif args.command == "finish":
        payload = finish_live_flow(
            args.discussion_dir.expanduser().resolve(),
            wrapper,
            args.spawn_order.expanduser().resolve(),
            [path.expanduser().resolve() for path in args.wait_result],
            args.round,
            args.phase,
            require_partial=args.require_partial,
            keep_tmp=args.keep_tmp,
            reset_transport=args.reset_transport,
        )
    else:
        payload = run_self_test(wrapper)

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
