import io
import unittest
from pprint import pprint as pp
from zoa import *

def assert_roundtrip(v):
  zoa = Zoa.from_(v)
  b = zoa.serialize()
  result_zoa = from_zoab(b)
  pp(result_zoa.arr)
  print()
  result = result_zoa.to_py()
  pp(v)
  pp(result)
  print(f'len: {len(v)} == {len(result)}')
  assert v == result

class TestZoa(unittest.TestCase):
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
    v = [Zoa.new_data(b'hi')]
    assert v[0].data == b'hi'
    write_arr(bw, v)
    b = bw.getvalue()
    print(b)
    assert b[0] == ZOA_ARR | 1
    assert b[1] == 2 # the string
    assert b[2:] == b'hi'

  def test_from_arr_str(self):
    v = from_zoab(io.BytesIO(b'\x02hi'))
    assert v == Zoa.new_data(b'hi')

  def test_from_to(self):
    assert_roundtrip([])
    assert_roundtrip([b'hi', b'bob'])
    assert_roundtrip([ [] ])
    assert_roundtrip([b'hi', [] ])
    assert_roundtrip([b'hi', [b'bob']])

  def test_long_bytes(self):
    bw = io.BytesIO()
    b = b'0123456789' * 13 # length = 130 (63 + 63 + 4
    write_data(bw, b)
    r = bw.getvalue()
    print(f"\n{hex(r[0])} == {hex(ZOA_DATA | ZOA_JOIN | 63)}\n")
    assert r[0] == ZOA_DATA | ZOA_JOIN | 63
    assert r[1:64] == b[0:63]
    assert r[64] == ZOA_DATA | ZOA_JOIN | 63
    assert r[65:128] == b[63:126]
    assert r[128] == ZOA_DATA | 4
    assert r[129:] == b[126:]

  def test_long_round(self):
    a = [ b'one', b'two', b'three', b'four', b'five' ] * 30 # 150
    assert_roundtrip(a)

if __name__ == '__main__':
  unittest.main()
