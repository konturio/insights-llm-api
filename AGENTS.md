# Notes for agents

- Check endpoints and database schema as described in `docs/`.
- Do not break indentation.
- Do not mix tabs and spaces.
- Format the code nicely and consistently.
- Write insightful code comments.
- Write enough comments so you can deduce what was a requirement in the future.
- Fix everything in the `docs/` folder to match reality.
- When refactoring to move a feature, don't forget to remove the original code path.
- Add enough debug logs so you can find out what's wrong but not be overwhelmed when something does not work as expected.
- Add empty lines between logical blocks as in the rest of the codebase.
- Values in layers should be absolute as much as possible: store "birthday" or "construction date" instead of "age".
- Prefer h3 resolution 11 unless you have other good reasons.
- Prefer indexed operators when dealing with jsonb ( `tags @> '{"key": "value"}` instead of `tags ->> 'key' = 'value'` ).
- SQL is lowercase, PostGIS functions follow their spelling from the manual (`st_segmentize` -> `ST_Segmentize`).
- Clean stuff up if you can: fix typos, make lexics more correct in Enghish.
