from __future__ import annotations

import asyncio

from actors.scripted import scanner, recon_bot, human_sim
from actors.llm import research_agent


async def main() -> None:
    ids = []
    for name, runner in [
        ("scanner", scanner.run),
        ("recon_bot", recon_bot.run),
        ("human_sim", human_sim.run),
        ("llm_agent", research_agent.run),
        ("scanner2", scanner.run),
        ("recon2", recon_bot.run),
        ("human2", human_sim.run),
        ("llm2", research_agent.run),
    ]:
        sid = await runner()
        ids.append((name, sid))
        print(f"{name}: {sid}")
    print(f"generated {len(ids)} sessions")


if __name__ == "__main__":
    asyncio.run(main())
