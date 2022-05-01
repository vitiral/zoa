import io
import unittest
from pprint import pprint as pp
from zoa import *

def assert_roundtrip(v):
  zoa = ZoaRaw.from_bytes(v)
  b = zoa.serialize()
  result_zoa = from_zoab(b)
  pp(result_zoa.arr)
  print()
  result = result_zoa.to_py()
  pp(v)
  pp(result)
  print(f'len: {len(v)} == {len(result)}')
  assert v == result

class TestZoaRaw(unittest.TestCase):
  def test_write_str(self):
    b = io.BytesIO()
    write_data(b, b'hi')
    b = b.getvalue()
    assert b[0] == 2
    assert b[1:] == b'hi'

  def test_write_arr_str(self):
    bw = io.BytesIO()
    v = [ZoaRaw.new_data(b'hi')]
    assert v[0].data == b'hi'
    write_arr(bw, v)
    b = bw.getvalue()
    print(b)
    assert b[0] == ZOA_ARR | 1
    assert b[1] == 2 # the string
    assert b[2:] == b'hi'

  def test_from_arr_str(self):
    v = from_zoab(io.BytesIO(b'\x02hi'))
    assert v == ZoaRaw.new_data(b'hi')

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


class TestBase(unittest.TestCase):
  def setUp(self):
    self.env = TyEnv()

class TestZoaTy(TestBase):
  def test_int(self):
    assert b'\x42' == Int(0x42).toZ().data
    assert 0x42 == Int.frZ(ZoaRaw.new_data(b'\x42'))

    z = Int(-0x42).toZ()
    assert len(z.arr) == 1
    assert b'\x42' == z.arr[0].data
    assert -0x42 == Int.frZ(ZoaRaw.new_arr([ZoaRaw.new_data(b'\x42')]))

  def test_arr_int(self):
    ArrInt = self.env.arr(Int)
    ai = ArrInt.frPy(range(10))
    z = ai.toZ()
    assert b'\x00' == z.arr[0].data
    assert b'\x09' == z.arr[9].data
    assert ai == ArrInt.frZ(z)

  def test_bytes(self):
    b = Bytes(b'abc 123')
    assert b'abc 123' == b.toZ().data
    assert b == Bytes.frZ(ZoaRaw.new_data(b'abc 123'))

  def test_struct(self):
    ty = self.env.struct(None, 'foo', [
        ('a', StructField(Int)),
    ])
    z = ZoaRaw.new_arr([
        Int(1).toZ(),  # numPositional
        Int(0x77).toZ(), # value of 'a'
    ])
    s = ty.frZ(z)
    assert s.a == 0x77
    assert z == s.toZ()

  def test_bitmap(self):
    ty = self.env.bitmap(None, 'bm', [
        ('a',     BmVar(0x01, 0x03)),
        ('b',     BmVar(0x03, 0x03)),
        ('noTop', BmVar(0x00, 0x10)),
        ('top',   BmVar(0x10, 0x10)),
    ])
    bm = ty();      assert 0 == bm.value
    bm.setTop();    assert 0x10 == bm.value
    bm.setNoTop();  assert 0x00 == bm.value
    bm.setA();      assert 0x01 == bm.value
    bm.setB();      assert 0x03 == bm.value
    bm.setA();      assert 0x01 == bm.value
    bm.setTop();    assert 0x11 == bm.value
    assert True == bm.isA()
    assert False == bm.isB()
    assert True == bm.isTop()

def tokens(buf):
  out, p = [], Parser(buf)
  while p.i < len(buf):
    t = p.token()
    if not t: break
    out.append(t.decode('utf-8'))
  return out

class TestParse(TestBase):
  def test_TG(self):
    assert TG.fromChr(ord(' ')) is TG.T_WHITE
    assert TG.fromChr(ord('\n')) is TG.T_WHITE
    assert TG.fromChr(ord('f')) is TG.T_HEX
    assert TG.fromChr(ord('g')) is TG.T_ALPHA
    assert TG.fromChr(ord('_')) is TG.T_ALPHA
    assert TG.fromChr(ord('.')) is TG.T_SINGLE

  def test_skipWhitespace(self):
    p = Parser(b'   \nfoo')
    assert p.i == 0
    p.skipWhitespace(); assert p.i == 4
    p.skipWhitespace(); assert p.i == 4

  def test_single(self):
    assert b']' == Parser(b']').token()
    assert b')' == Parser(b')').token()
    assert b'a' == Parser(b'a').token()

  def test_tokens(self):
    assert tokens(b'a_b[foo.bar baz]') == [
      'a_b', '[', 'foo', '.', 'bar', 'baz', ']']

  def test_struct(self):
    p = Parser(b'struct foo [a: Int]')
    p.parse()
    foo = p.env.tys[b'foo']
    assert foo._fields == [(b'a', StructField(Int))]

    p = Parser(b'struct ab [a: Int; b: Bytes]')
    p.parse()
    ab = p.env.tys[b'ab']
    assert ab._fields == [
      (b'a', StructField(Int)),
      (b'b', StructField(Bytes)),
    ]

  def test_struct_inner(self):
    p = Parser(b'struct Foo [a: Int]\nstruct Bar[a: Int; f: Foo]')
    p.parse()
    Foo = p.env.tys[b'Foo']
    Bar = p.env.tys[b'Bar']
    assert Bar._fields == [
      (b'a', StructField(Int)),
      (b'f', StructField(Foo)),
    ]


if __name__ == '__main__':
  unittest.main()
