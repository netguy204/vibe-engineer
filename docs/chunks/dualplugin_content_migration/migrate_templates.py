"""One-time migration: derive src/templates/plugin/ templates from committed renders.

Chunk artifact for docs/chunks/dualplugin_content_migration. Run once from the
repo root (`uv run python docs/chunks/dualplugin_content_migration/migrate_templates.py`).

For each committed commands/*.md and agents/*.md (the two wave-1 pilots
excluded), this script:

1. parses the frontmatter and body,
2. emits a template per the TEMPLATING_GUIDE §6 recipe (canonical preamble
   collapsed into the idiom macro, probe lines into idioms.probe, body
   byte-verbatim),
3. SELF-VERIFIES: renders the written template in the claude flavor and
   asserts the output equals the committed file with exactly one inserted
   generated-marker line. Any other diff aborts loudly.

This makes the chunk's byte-stability bar an executable check.
"""

import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

import plugin_render  # noqa: E402
from template_system import get_environment  # noqa: E402

TPL_ROOT = REPO / "src" / "templates" / "plugin"
IMPORT_LINE = '{%- import "partials/" ~ flavor ~ "/idioms.md.jinja2" as idioms -%}'

PILOTS = {"commands/chunk-create.md", "commands/ve-status.md"}

# Nonstandard context blocks (extra probes beyond the standard three): keep
# their own ## Context heading, replace probe lines with idioms.probe.
NONSTANDARD_CONTEXT = {"commands/chunk-commit.md", "commands/chunk-execute-all.md"}

PROBE_RE = re.compile(r"^- (.+?): !`(.+)`$")


def jstr(s: str) -> str:
    """Emit s as a Jinja2 string literal, choosing quote style per content."""
    if '"' not in s:
        return f'"{s}"'
    if "'" not in s:
        return f"'{s}'"
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def canonical_preamble_text() -> str:
    env = get_environment("plugin")
    tpl = env.from_string(IMPORT_LINE + "\n{{ idioms.canonical_preamble() }}")
    return tpl.render(flavor="claude")


def split_frontmatter(text: str) -> tuple[list[str], str]:
    assert text.startswith("---\n"), "file must open with frontmatter"
    end = text.index("\n---\n", 4)
    fm_lines = text[4:end].split("\n")
    body = text[end + len("\n---\n") :]
    assert body.startswith("\n"), "expected a blank line after frontmatter"
    return fm_lines, body[1:]


def parse_command_frontmatter(fm_lines: list[str]) -> tuple[str, str, list[str]]:
    assert len(fm_lines) == 3, fm_lines
    name = fm_lines[0].removeprefix("name: ")
    desc = fm_lines[1].removeprefix("description: ")
    assert fm_lines[2].startswith("allowed-tools: "), fm_lines[2]
    tools_raw = fm_lines[2].removeprefix("allowed-tools: ")
    tools = tools_raw.split(", ")
    assert ", ".join(tools) == tools_raw, "allowed-tools must round-trip"
    return name, desc, tools


def frontmatter_call(name: str, desc: str, tools: list[str]) -> str:
    tools_lit = ", ".join(jstr(t) for t in tools)
    return (
        "{{ idioms.frontmatter(\n"
        f"    {jstr(name)},\n"
        f"    {jstr(desc)},\n"
        f"    [{tools_lit}]\n"
        ") }}"
    )


def extract_caller(after_canon: str) -> str:
    """Caller bullets: lines following the canonical block until a blank line
    that precedes a heading or horizontal rule.

    Caller content must directly continue the runtime-context bullet list
    (single newline after the canonical block). A blank line right after the
    block means the next paragraph is ordinary body text, not caller content
    — the `{% call %}` mechanism inserts exactly one newline, so a
    blank-line-separated paragraph must stay verbatim in the template body.
    """
    if after_canon.startswith("\n\n"):
        return ""
    lines = after_canon.split("\n")
    caller: list[str] = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln == "" and i + 1 < len(lines) and (
            lines[i + 1].startswith("#") or lines[i + 1].startswith("---")
        ):
            break
        caller.append(ln)
        i += 1
    return "\n".join(caller)


def replace_probe_lines(body: str) -> str:
    """In a nonstandard Context block, swap each probe line for idioms.probe."""
    start = body.index("## Context")
    end = body.index("## Runtime context", start)
    head, region, tail = body[:start], body[start:end], body[end:]
    out_lines = []
    replaced = 0
    for ln in region.split("\n"):
        m = PROBE_RE.match(ln)
        if m:
            label, command = m.group(1), m.group(2)
            out_lines.append(
                "{{ idioms.probe(%s, %s) }}" % (jstr(label), jstr(command))
            )
            replaced += 1
        else:
            out_lines.append(ln)
    assert replaced >= 3, "expected at least the three standard probes"
    return head + "\n".join(out_lines) + tail


def build_command_template(body: str, fm_lines: list[str], canon: str) -> str:
    name, desc, tools = parse_command_frontmatter(fm_lines)
    head = (
        IMPORT_LINE
        + "\n"
        + frontmatter_call(name, desc, tools)
        + "\n\n{{ idioms.generated_marker(source_template) }}\n"
    )
    idx = body.find(canon)
    if idx == -1:
        # Nonstandard context block: probes only.
        return head + replace_probe_lines(body)
    after = body[idx + len(canon) :]
    caller = extract_caller(after)
    if caller.strip():
        block = (
            "{% call idioms.canonical_preamble() -%}\n"
            + caller.strip("\n")
            + "\n{%- endcall %}"
        )
        replaced = body[:idx] + block + after[len(caller) :]
    else:
        replaced = (
            body[:idx] + "{{ idioms.canonical_preamble() }}" + after
        )
    return head + replaced


def build_agent_template(body: str, fm_lines: list[str]) -> str:
    fm_text = "---\n" + "\n".join(fm_lines) + "\n---"
    return (
        IMPORT_LINE
        + "\n"
        + fm_text
        + "\n\n{{ idioms.generated_marker(source_template) }}\n"
        + body
    )


def expected_render(text: str, template_name: str) -> str:
    """The committed file with exactly the marker line inserted after the
    frontmatter's blank line."""
    end = text.index("\n---\n", 4)
    head = text[: end + len("\n---\n")] + "\n"
    rest = text[len(head) :]
    marker = (
        f"<!-- GENERATED from src/templates/plugin/{template_name} — edit "
        "that template and run `ve plugin render`; direct edits here will "
        "be overwritten. -->"
    )
    return head + marker + "\n" + rest


def migrate(kind: str) -> int:
    canon = canonical_preamble_text()
    count = 0
    for path in sorted((REPO / kind).glob("*.md")):
        rel = f"{kind}/{path.name}"
        if rel in PILOTS:
            continue
        template_name = f"{kind}/{path.name}.jinja2"
        text = path.read_text()
        fm_lines, body = split_frontmatter(text)
        if kind == "commands":
            template = build_command_template(body, fm_lines, canon)
        else:
            template = build_agent_template(body, fm_lines)
        out = TPL_ROOT / kind / f"{path.name}.jinja2"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(template if template.endswith("\n") else template + "\n")

        fresh = plugin_render.render_plugin_template(template_name)
        expected = expected_render(text, template_name)
        if fresh != expected:
            import difflib

            diff = "\n".join(
                difflib.unified_diff(
                    expected.splitlines(),
                    fresh.splitlines(),
                    "expected",
                    "fresh-render",
                    lineterm="",
                )
            )
            out.unlink()
            raise SystemExit(
                f"BYTE-STABILITY FAILURE for {rel}:\n{diff[:4000]}"
            )
        count += 1
        print(f"migrated {rel} -> {out.relative_to(REPO)}")
    return count


def main() -> None:
    n_cmd = migrate("commands")
    n_agent = migrate("agents")
    print(f"\nOK: {n_cmd} commands + {n_agent} agents migrated, all byte-stable")


if __name__ == "__main__":
    main()
