# Project Notes

## Ingest Errors (2026-04-05)

The following files failed during ingest script execution:

- **A_Test_Rose.epub**: error return without exception set
- **Come Follow To You vol3.pdf**: bad parameter or other API misuse
- **Come Follow To You vol2.pdf**: bad parameter or other API misuse
- **DhammapadVol1.pdf**: bad parameter or other API misuse
- **Early Talks.pdf**: bad parameter or other API misuse

Likely causes: PDF extraction issues (possibly encrypted/permission-restricted PDFs) and EPUB parsing errors.

## Gitignore & Book Files

The `.gitignore` is set up to ignore all PDFs/EPUBs in `books/` except for `A_Test_Rose.*` test files. This keeps the 200+ Osho books local-only while allowing server-side testing to work.

**If you want to make this fully web-deployable later:** You'll need to either:
- Host the books separately (S3, etc.) and download them at runtime
- Or remove the gitignore exceptions and commit specific books you have rights to share
- Or use a different storage strategy entirely

