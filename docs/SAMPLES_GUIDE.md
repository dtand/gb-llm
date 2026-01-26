## Guide

This is a guide for local sample generation.  Local sample generation is an LLM <-> human feedback loop which happens in the IDE.  The goal is to iterate between the agent and the human to create more unique samples in the /games/samples folder, which serves as a corpus of gameboy game demos.  Eventually building up to a very large library of working samples.  Here are the steps for a new sample generation:

1. LLM shall suggest new categories to generate samples for (new samples shall be suggested based on what is already implemented in games/samples)

2. Human will approve or deny categories

3. Agent will implement new sample, then prompt human to test

4. LLM and human will iterate until ROM is fully functional

5. Once ROM is marked done, the sample will be complete and added to the manifest.json

6. Repeat 3-5 for new sample, log any meaningful bugs to the bugs/ folder that can be used for reference

7. When done with all samples, inject them into the corpus vector db using `python src/corpus/indexer.py` (be sure to activate venv/bin/activate)