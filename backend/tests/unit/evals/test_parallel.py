import threading
import time

from evals import deepeval_run


def case(i):
    return {"id": f"c{i}", "kind": "data", "question": f"q{i}"}


def fake_run_case(container, executor, judge, role, c):
    time.sleep(0.05 * (3 - int(c["id"][1:])))  # later cases finish first
    if c["id"] == "c1":
        raise RuntimeError("boom")
    return {"role": role, "id": c["id"], "kind": "data", "question": c["question"], "answer": "",
            "sql": [], "scores": {"result_match": 1.0}, "reasons": {}, "passed": True}


def test_parallel_run_keeps_input_order_and_turns_a_crash_into_a_failure(monkeypatch):
    monkeypatch.setattr(deepeval_run, "run_case", fake_run_case)
    jobs = [("business_owner", case(i)) for i in range(3)]
    results = deepeval_run.run_parallel(None, None, None, jobs, workers=3)
    assert [r["id"] for r in results] == ["c0", "c1", "c2"]
    assert results[1]["passed"] is False and "boom" in results[1]["reasons"]["run_error"]
    assert results[0]["passed"] and results[2]["passed"]


def test_cases_really_run_at_the_same_time(monkeypatch):
    seen, lock = set(), threading.Lock()

    def slow(container, executor, judge, role, c):
        with lock:
            seen.add(threading.current_thread().name)
        time.sleep(0.1)
        return {"role": role, "id": c["id"], "kind": "data", "question": "", "answer": "",
                "sql": [], "scores": {}, "reasons": {}, "passed": True}

    monkeypatch.setattr(deepeval_run, "run_case", slow)
    start = time.monotonic()
    deepeval_run.run_parallel(None, None, None, [("business_owner", case(i)) for i in range(6)],
                              workers=6)
    assert time.monotonic() - start < 0.4 and len(seen) > 1


def test_judge_calls_are_retried_then_give_up(monkeypatch):
    monkeypatch.setattr(deepeval_run.time, "sleep", lambda _: None)

    class Flaky:
        calls = 0

        def measure(self, tc, **kw):
            Flaky.calls += 1
            if Flaky.calls < 3:
                raise RuntimeError("429")

    deepeval_run.measure_with_retry(Flaky(), None)
    assert Flaky.calls == 3

    class Dead:
        def measure(self, tc, **kw):
            raise RuntimeError("down")

    import pytest
    with pytest.raises(RuntimeError):
        deepeval_run.measure_with_retry(Dead(), None)
