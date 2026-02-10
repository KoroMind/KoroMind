"""Shared model identifier validation rules."""

import re

MODEL_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
