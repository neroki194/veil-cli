## about
**veil** is OSINT tool that checks whether a site is blocked in a country, straight from your terminal, developed by [maher](https://github.com/neroki194).

the idea is simple: type a site, get a verdict, see which countries show blocking signal, page through the full picture if you want it.

 > [!WARNING]
 > laws on checking or discussing censorship vary by country. **veil** only
 > reads public OONI data. it doesn't access, proxy, or bypass anything.

## tech stack
- python (requests, rich)
- visual studio code
- some coffee


## what it does
it does this by reading public measurement data from [OONI](https://ooni.org), a network of volunteer probes around the world that continuously test whether sites are reachable from their country. `veil` doesn't run its own network tests against a target country. It reads what OONI's probes have already reported.

alongside the OONI verdict, veil also gathers basic details about the site itself: its resolved IP, hosting organization and ASN, a quick HTTP check, and the page title. this part reflects your own machine's vantage point, not the target country, and is shown as separate context.

 > [!NOTE]
 > results come from OONI's crowdsourced data, not a live test. sparse
 > coverage can show `NO DATA` even where access is actually blocked.

 > [!CAUTION]
 > don't rely on this as your only source for anything. OONI can't give
 > complete or fully valid info. double-check whether the information
 > is valid.

## install
download [Python](https://python.org/downloads) for your os and run this command on your terminal:

```bash
pip install veil-cli
```

on systems that block plain `pip install` outside a virtual environment (arch and others enforcing PEP 668), use `pipx` instead:

```bash
pipx install veil-cli
```

## features
- **country check**: give it a site and a country, get back a clear verdict: blocked, likely blocked, reachable, or no data
- **list all countries**: leave the country blank to see every country with any OONI data for that site, sorted worst first
- **paginated output**: large results are shown a page at a time instead of flooding your terminal in one go
- **site details**: resolved IP, hosting organization, ASN, a quick HTTP check, and the page title, gathered from your own machine
- **name or code**: type a country name or its two letter code, both work
- **interactive shell**: run `veil` with no arguments for a guided, boxed prompt session
- **one shot mode**: run it as a single command for scripting or quick checks
- **honest about gaps**: countries with too little OONI coverage are shown as no data, never folded into a reassuring summary

## star history

<a href="https://www.star-history.com/?repos=neroki194%2Fveil-cli&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=neroki194/veil-cli&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=neroki194/veil-cli&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=neroki194/veil-cli&type=date&legend=top-left" />
 </picture>
</a>
