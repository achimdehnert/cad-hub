---
description: Testing Conventions — T-01/T-02/T-03
---

# Testing Conventions

## T-01: `pytest.importorskip`
```bash
grep -rn "^from aifw\|^from promptfw" tests/
```

## T-02: `AsyncMock(side_effect=)` statt `wraps=`
```bash
grep -rn "AsyncMock(wraps=" tests/
```

## T-03: `pytest.raises()` für Exceptions
```bash
grep -rn "def test_.*fallback" tests/
```

```bash
pytest tests/ -v --tb=short
```
