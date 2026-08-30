def paginate(total_results: int, page: int, page_size: int):
    start = (page - 1) * page_size
    end = start + page_size
    total_pages = (total_results + page_size - 1) // page_size if total_results else 0
    return start, end, total_pages


def test_first_page():
    start, end, total_pages = paginate(25, 1, 10)
    assert start == 0 and end == 10 and total_pages == 3


def test_last_page():
    start, end, total_pages = paginate(25, 3, 10)
    assert start == 20 and end == 30 and total_pages == 3


def test_no_results():
    start, end, total_pages = paginate(0, 1, 10)
    assert total_pages == 0


def test_exact_multiple():
    _, _, total_pages = paginate(20, 1, 10)
    assert total_pages == 2


def test_api_routes_registered():
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from api import main
    paths = {r.path for r in main.app.routes}
    assert "/search" in paths
    assert "/crawl" in paths
    assert "/status" in paths


if __name__ == "__main__":
    test_first_page()
    test_last_page()
    test_no_results()
    test_exact_multiple()
    test_api_routes_registered()
    print("All Day 5 API tests passed.")
