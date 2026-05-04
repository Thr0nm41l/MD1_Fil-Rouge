# DAG — `test__print_hello`

**File:** `dags/test__print_hello.py`
**Tags:** `test`
**Schedule:** None (manual trigger only)
**Catchup:** disabled
**Max active runs:** 1

---

## Purpose

Minimal smoke-test DAG. Verifies that the Airflow scheduler is running, the worker pool is healthy, and task execution works end-to-end — with no external dependencies or side effects.

---

## Task Graph

```
start ──► print_hello ──► end (ALL_DONE)
```

---

## Tasks

### `start`
Empty marker task. Entry point of the DAG.

---

### `print_hello`
**Operator:** `PythonOperator`

Prints a single line to the task log:

```
Hello, I am a test DAG that prints 'hello' to the logs!
```

No database connection, no parameters, no XCom output.

---

### `end`
Empty marker task. `TriggerRule.ALL_DONE`.

---

## Notes

- No parameters, no connections required
- Use this DAG to confirm the Airflow deployment is operational after a cluster restart or infrastructure change
