# Submission documents

Prepared 24 November 2026 from the implementation, original proposal and retained
verification evidence.

| File | Submit or use for |
| --- | --- |
| Project_Report.pdf | Main 17-page semester report, with embedded ER diagrams, dictionary, SQL examples, screenshots, test evidence and limitations. |
| Project_Report.docx | Editable Word version of the same report. |
| ER_Diagram.pdf | Complete 3-page landscape ERD: role/permission policy; resources and audit; authentication support and full FK inventory. |
| schema_snapshot.json | Technical input to the document generator; 10 modeled tables, 62 attributes, 12 FKs. Not a separate submission requirement. |

Group members, student IDs and instructor were taken from the supplied proposal.
No university name, course section, instructor-specific rubric or declaration was
supplied, so none was invented. Check your course's cover-page/file-format rules
and the spelling of those supplied names before uploading.

The ER diagram includes primary/composite keys, references, nullability,
candidate-key notes and a cardinality legend. Reference boxes repeat APP_USER
and ROLE for readability; they are not additional tables. Policy target strings
are historical identifiers, not invented foreign keys. The Alembic version table
is migration metadata and is outside the application ER model.

The main report cites the actual 22 November 2026 results: 113 backend/PostgreSQL,
12 React and 5 browser tests passed. They were not rerun during this documentation
pass. The local PostgreSQL port was unavailable during the review; consistency
was reviewed using ORM metadata, the canonical migration, generated SQL and the
retained successful schema-comparison test evidence. No software changes were made.

To regenerate using the document runtime, from the repository root:

```sh
# Replace the absolute runtime paths if your bundled runtime is installed elsewhere.
/home/ali/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/build_submission.py --erd
/home/ali/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/override/pdftoppm -scale-to 1800 -png docs/submission/ER_Diagram.pdf artifacts/submission-qa/erd
/home/ali/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/build_submission.py --report
```

Use the document skill's render_docx.py to render and visually verify any revised
DOCX, then replace the PDF with that verified render. Keep schema_snapshot.json
synchronized with model changes. Academic report styling uses black headings,
readable tables and mixed portrait/landscape pages; diagrams are vector PDFs.

## Writing revision

The report was edited on 24 November 2026 for clearer academic prose, practical
examples and less repetition. The schema, SQL, screenshots, group identities and
recorded test results were retained. No personal experiences, individual
contributions or claims of independent authorship were invented. This was an
editorial review, not an AI-detector or plagiarism scan. The group should review
the wording and check its course rules before submission.
