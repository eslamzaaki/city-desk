"""Keep tests on DeskChatModel when a developer .env names a provider."""

from __future__ import annotations

import os

os.environ["CITYDESK_PROVIDER"] = "local"
os.environ["CITYDESK_MODEL"] = ""
