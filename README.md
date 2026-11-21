# The Day in World News: Saturday 21 November 2026

A one-page newspaper front page summing up 21 November 2026: **46 stories, 7 regions**.

- 3 illustrated lead stories (Kryvyi Rih strike, Sinaloa cartel capture, COP31 overtime)
- 9 secondary stories
- A "By the Numbers" strip and a UTC timeline of the day
- 34 one-line briefs, plus sources and a date-verification line

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
# writes out/entry.png (1024x1024 PNG, under 1 MiB)
```

Pure Python standard library, no network. Two runs produce byte-identical output.

Every story was verified as having happened, or first been reported, on
21 November 2026. Disputed claims are attributed in the image.
