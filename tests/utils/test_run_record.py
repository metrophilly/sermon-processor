import json

import pytest

from app.utils.run_record import write_run_record


def test_a_record_is_written_next_to_the_output(tmp_path):
    path = write_run_record(str(tmp_path / "2026-11-01.wav"), {"date": "2026-11-01", "fade": 1.0})
    assert path == str(tmp_path / "2026-11-01.json")
    saved = json.loads(open(path).read())
    assert saved["date"] == "2026-11-01" and "created_at" in saved


def test_numpy_numbers_and_booleans_are_saved_as_plain_json(tmp_path):
    numpy = pytest.importorskip("numpy")
    record = {
        "start": numpy.float64(2459.66),
        "small": numpy.float32(1.5),
        "count": numpy.int64(3),
        # This is what crashed a real run: comparing NumPy floats gives a NumPy bool.
        "adjusted": numpy.float64(5.0) > numpy.float64(1.0),
        "nested": {"flags": [numpy.bool_(True), numpy.bool_(False)]},
    }

    path = write_run_record(str(tmp_path / "out.wav"), record)

    saved = json.loads(open(path).read())
    assert saved["start"] == pytest.approx(2459.66)
    assert saved["count"] == 3
    assert saved["adjusted"] is True
    assert saved["nested"]["flags"] == [True, False]


def test_odd_values_never_stop_a_record_from_being_written(tmp_path):
    class Strange:
        def __str__(self):
            return "strange value"

    path = write_run_record(
        str(tmp_path / "out.wav"), {"a": {1, 2}, "b": (3, 4), "c": Strange()}
    )

    saved = json.loads(open(path).read())
    assert sorted(saved["a"]) == [1, 2]
    assert saved["b"] == [3, 4]
    assert saved["c"] == "strange value"
