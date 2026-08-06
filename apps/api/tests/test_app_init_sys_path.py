"""app/__init__.py가 packages/를 찾아 sys.path에 넣는지 확인 (Docker에서 IndexError 재발 방지)."""
import importlib
import unittest


class TestAppInitSysPath(unittest.TestCase):
    def test_packages_rag_importable(self):
        # app 패키지를 import하는 시점에 __init__.py가 리포 루트를 sys.path에 추가해야 함.
        importlib.import_module("app")
        importlib.import_module("packages.rag.retriever")


if __name__ == "__main__":
    unittest.main()
