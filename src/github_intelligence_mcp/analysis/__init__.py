"""Deterministic repository health analysis.

Pure computation layer: scorers take explicit inputs (models or counts) and
return ``(score, evidence)`` tuples. No I/O, no MCP dependencies — fully
unit-testable and reusable by future agents or CLIs.
"""
