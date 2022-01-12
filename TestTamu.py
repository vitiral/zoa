import io
import unittest
from tamu import *

def assert_roundtrip(v):
  sab = Sab.from_(v)
  b = sab.serialize()
  result_sab = from_sab(b)
  result = result_sab.to_py()
  assert v == result

class TestSan(unittest.TestCase):
  def test_pass(self):
    pass

  def test_write_str(self):
    b = io.BytesIO()
    write_data(b, b'hi')
    b = b.getvalue()
    assert b[0] == 2
    assert b[1:] == b'hi'

  def test_write_arr_str(self):
    bw = io.BytesIO()
    v = [Sab.new_data(b'hi')]
    assert v[0].data == b'hi'
    write_arr(bw, v)
    b = bw.getvalue()
    print(b)
    assert b[0] == SAB_ARR | 1
    assert b[1] == 2 # the string
    assert b[2:] == b'hi'

  def test_from_arr_str(self):
    v = from_sab(io.BytesIO(b'\x02hi'))
    assert v == Sab.new_data(b'hi')

  def test_from_to(self):
    assert_roundtrip([])
    assert_roundtrip([b'hi', b'bob'])
    assert_roundtrip([ [] ])
    assert_roundtrip([b'hi', [] ])
    assert_roundtrip([b'hi', [b'bob']])

if __name__ == '__main__':
  unittest.main()
