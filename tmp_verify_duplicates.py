import os
import sys

os.chdir(r'c:\Users\Administrator\Downloads\doantotnghiepv7\api-prescription-ocr')
sys.path.insert(0, '.')

import pytest

raise SystemExit(pytest.main(['-q', 'tests/test_prescription_flow.py', '-k', 'merge_duplicate']))
