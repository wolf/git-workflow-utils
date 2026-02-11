"""Branch description parsing and formatting using git trailer conventions."""

import re
from dataclasses import dataclass, field


_TRAILER_RE = re.compile(r"^([A-Za-z][A-Za-z0-9-]*)\s*:\s*(.+)$")


@dataclass
class BranchDescription:
    """
    Structured representation of a git branch description.

    A branch description has two parts:
    - `summary`: free-form text (like a commit message subject+body)
    - `trailers`: structured `Key: value` pairs in git trailer format

    Trailer keys are stored in their original case. Lookups via `get`
    and `get_all` are case-insensitive.

    """

    summary: str = ""
    trailers: dict[str, list[str]] = field(default_factory=dict)

    def _find_key(self, key: str) -> str | None:
        """Find the stored key matching a case-insensitive lookup."""
        key_lower = key.lower()
        for k in self.trailers:
            if k.lower() == key_lower:
                return k
        return None

    def get(self, key: str) -> str | None:
        """
        Get the first value for a trailer key (case-insensitive).

        Returns None if the key is not present.

        """
        if stored_key := self._find_key(key):
            values = self.trailers[stored_key]
            return values[0] if values else None
        return None

    def get_all(self, key: str) -> list[str]:
        """
        Get all values for a trailer key (case-insensitive).

        Returns an empty list if the key is not present.

        """
        if stored_key := self._find_key(key):
            return list(self.trailers[stored_key])
        return []

    def replace(self, key: str, value: str) -> None:
        """
        Replace all values for a trailer key with a single value.

        Uses the provided key casing. If a key with different casing
        already exists, it is removed first.

        """
        if (stored_key := self._find_key(key)) and stored_key != key:
            del self.trailers[stored_key]
        self.trailers[key] = [value]

    def add(self, key: str, value: str) -> None:
        """
        Add a value to a trailer key (for multi-valued trailers).

        Appends to existing values if the key is present. Uses the
        existing key casing if present, otherwise uses the provided casing.

        """
        stored_key = self._find_key(key) or key
        self.trailers.setdefault(stored_key, []).append(value)

    @property
    def tickets(self) -> list[str]:
        """Get all Ticket trailer values."""
        return self.get_all("Ticket")

    @property
    def remote(self) -> str | None:
        """Get the Remote trailer value."""
        return self.get("Remote")

    @property
    def pr(self) -> str | None:
        """Get the PR trailer value."""
        return self.get("PR")


def parse_branch_description(text: str) -> BranchDescription:
    """
    Parse a branch description string into a `BranchDescription`.

    Finds a contiguous block of trailer lines at the end of the text.
    Everything before the trailer block (minus blank separator) is the
    summary. Handles legacy descriptions that are all trailers with no
    summary, and plain text descriptions with no trailers.

    """
    text = text.strip()
    if not text:
        return BranchDescription()

    lines = text.split("\n")

    # Scan backward from the end to find the contiguous trailer block.
    trailer_start = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i].strip()
        if _TRAILER_RE.match(line):
            trailer_start = i
        elif line == "":
            # Blank line: if we found trailers below, this is the separator
            break
        else:
            # Non-trailer, non-blank line: no trailer block here
            trailer_start = len(lines)
            break

    # Extract trailers
    trailers: dict[str, list[str]] = {}
    for line in lines[trailer_start:]:
        if m := _TRAILER_RE.match(line.strip()):
            key, value = m.group(1), m.group(2).strip()
            trailers.setdefault(key, []).append(value)

    # Everything before the trailer block (and blank separator) is the summary
    summary_end = trailer_start
    while summary_end > 0 and lines[summary_end - 1].strip() == "":
        summary_end -= 1

    summary = "\n".join(lines[:summary_end]).strip()

    return BranchDescription(summary=summary, trailers=trailers)


def format_branch_description(desc: BranchDescription) -> str:
    """
    Format a `BranchDescription` into a string for git config.

    Produces summary text, a blank separator line, then trailers.
    Omits empty sections.

    """
    parts: list[str] = []

    if desc.summary:
        parts.append(desc.summary)

    trailer_lines = []
    for key, values in desc.trailers.items():
        for value in values:
            trailer_lines.append(f"{key}: {value}")

    if trailer_lines:
        if parts:
            parts.append("")  # blank separator
        parts.append("\n".join(trailer_lines))

    return "\n".join(parts)


def build_branch_description(
    *,
    tickets: str | list[str] | None = None,
    remote: str | None = None,
    branch_type: str | None = None,
    author: str | None = None,
    created_from: str | None = None,
    summary: str = "",
) -> BranchDescription:
    """
    Build a `BranchDescription` for a newly created branch.

    All parameters are optional. This is the structured replacement for
    the inline f-string that scripts use to build descriptions.

    """
    desc = BranchDescription(summary=summary)

    if tickets is not None:
        if isinstance(tickets, str):
            tickets = [tickets]
        for t in tickets:
            desc.add("Ticket", t)

    if remote is not None:
        desc.replace("Remote", remote)

    if branch_type is not None:
        desc.replace("Type", branch_type)

    if author is not None:
        desc.replace("Author", author)

    if created_from is not None:
        desc.replace("Created-from", created_from)

    return desc
