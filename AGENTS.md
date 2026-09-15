# Repository roles

During an AutoResearch strategy experiment, read program.md first.

- Editable: strategy/strategy.py only. Keep the candidate self-contained; helper
  modules are not included in the current single-file snapshot contract.
  Importing the provided read-only core.indicators library is allowed.
- Read-only: config/, core/, run.py, README.md, program.md, and this file.
  The researcher sets config/ before preparation; its hashes freeze for the run.
- Runner-owned: runs/. Read results and logs; never edit archived experiments,
  champion, locks, or freeze records manually.
- Data: fit receives training data; validation is evaluated through run.py.
  Never inspect validation labels or locate/read the external final holdout.
- Researcher-only: data/, prepare.py, examples/, tests/ and docs/; external raw data and final reports.
  Bundled full histories must not be exposed to a research agent. prepare.py creates
  a separate study workspace without data/; run the agent there.
  After preparing, expose only the research files and cache to the agent.

Explicit user requests for framework maintenance or data preparation authorize
edits outside strategy/; this does not authorize changing an existing frozen run.
Directory roles and hashes detect mistakes; OS/container permissions must enforce
access boundaries when deploying an untrusted agent.
