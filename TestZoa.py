import io
import unittest
from zoa import *

def assert_roundtrip(v):
  zoa = ZoaRaw.frPy(v)
  b = zoa.serialize()
  result_zoa = from_zoab(b)
  result = result_zoa.to_py()
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

  def test_long_data(self):
    bw = io.BytesIO()
    b = b'0123456789' * 13 # length = 130 (63 + 63 + 4
    write_data(bw, b)
    r = bw.getvalue()
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

  def test_data(self):
    b = Data(b'abc 123')
    assert b'abc 123' == b.toZ().data
    assert b == Data.frZ(ZoaRaw.new_data(b'abc 123'))

  def test_struct(self):
    ty = self.env.struct(None, b'foo', [
        (b'a', StructField(Int)),
    ])
    z = ZoaRaw.new_arr([
        Int(1).toZ(),  # numPositional
        Int(0x77).toZ(), # value of 'a'
    ])
    s = ty.frZ(z)
    assert s.a == 0x77
    assert z == s.toZ()

  def test_enum(self):
    ty = self.env.enum(None, b'en', [
        (b'a',     Int),
        (b'b',     Data),
    ])
    en = ty(a=Int(3))
    assert en.b is None;    assert 3 == en.a
    assert en.toZ() == ZoaRaw.new_arr([Int(0).toZ(), Int(3).toZ()])
    en = ty(b=Data(b'hi there enum'))
    assert en.a is None;     assert en.b == b'hi there enum'
    assert en.toZ() == ZoaRaw.new_arr([
      Int(1).toZ(), Data(b'hi there enum').toZ()])
    assert ty.frZ(en.toZ()) == en

  def test_bitmap(self):
    ty = self.env.bitmap(None, b'bm', [
        (b'a',     BmVar(0x01, 0x03)),
        (b'b',     BmVar(0x03, 0x03)),
        (b'noTop', BmVar(0x00, 0x10)),
        (b'top',   BmVar(0x10, 0x10)),
    ])
    bm = ty();       assert 0 == bm.value
    bm.set_top();    assert 0x10 == bm.value
    bm.set_noTop();  assert 0x00 == bm.value
    bm.set_a();      assert 0x01 == bm.value
    assert 0x01 == bm.get_a()
    bm.set_b();      assert 0x03 == bm.value
    assert 0x03 == bm.get_a()
    bm.set_a();      assert 0x01 == bm.value
    bm.set_top();    assert 0x11 == bm.value
    assert  bm.is_a()
    assert not bm.is_b()
    assert bm.is_top()
    bm.set_a(0x03);  assert bm.is_b();  assert 0x13 == bm.value
    assert bm.toZ() == ZoaRaw.new_data(b'\x13')
    assert bm.frZ(bm.toZ()) == bm

  def test_dyn(self):
    i = Dyn._int(4)
    assert i.ty == DynType.Int
    i = Dyn.frPy(4)
    assert i.ty == DynType.Int
    assert i.value == 4
    assert i.frZ(i.toZ()) == i

  def test_dynArr(self):
    a = Dyn.frPyArrInt([1, 2, 3, 4])
    assert a.value == [1, 2, 3, 4]
    assert a.frZ(a.toZ()) == a

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
    assert TG.fromChr(ord('_')) is TG.T_NUM
    assert TG.fromChr(ord('f')) is TG.T_HEX
    assert TG.fromChr(ord('g')) is TG.T_ALPHA
    assert TG.fromChr(ord('.')) is TG.T_ALPHA

  def test_data(self):
    b = Data(b'hi there bob!')
    expected = '  68 6920 7468 6572 6520 626F 6221'
    result = repr(b)
    assert expected == result

    b = Data(b'\x10\x12')
    assert '1012' == repr(b)

  def test_skipWhitespace(self):
    p = Parser(b'   \nfoo')
    assert p.i == 0
    p.skipWhitespace(); assert p.i == 4
    p.skipWhitespace(); assert p.i == 4

  def test_comment(self):
    Parser(b'\\ hi there\n \\hi \\there\n \\(hi there) \\bob').parse()

  def test_single(self):
    assert b']' == Parser(b']').token()
    assert b')' == Parser(b')').token()
    assert b'a' == Parser(b'a').token()

  def test_tokens(self):
    assert tokens(b'a_b[foo.bar baz]') == [
      'a_b', '[', 'foo.bar', 'baz', ']']

  def test_struct(self):
    p = Parser(b'struct foo [a: Int]')
    p.parse()
    foo = p.env.tys[b'foo']
    assert foo._fields == [(b'a', StructField(Int))]

    p = Parser(b'struct Ab [a: Int; b: Data]')
    p.parse()
    Ab = p.env.tys[b'Ab']
    assert Ab._fields == [
      (b'a', StructField(Int)),
      (b'b', StructField(Data)),
    ]
    ab = Ab(a = 1, b = b'hi')
    assert ab.a == 1
    assert ab.b == b'hi'

  def test_struct_inner(self):
    p = Parser(b'struct Foo [a: Int]\nstruct Bar[a: Int; f: Foo]')
    p.parse()
    Foo = p.env.tys[b'Foo']
    Bar = p.env.tys[b'Bar']
    assert Bar._fields == [
      (b'a', StructField(Int)),
      (b'f', StructField(Foo)),
    ]

  def test_enum(self):
    p = Parser(b'enum E \\comment [a: Int; b: Data]')
    p.parse()
    E = p.env.tys[b'E']
    assert E._variants == [
      (b'a', Int),
      (b'b', Data),
    ]

  def test_bitmap(self):
    p = Parser(b'bitmap B [a 0x01 0x03; b 0x02 0x07]')
    p.parse()
    B = p.env.tys[b'B']
    assert B._variants == [
      (b'a', BmVar(1, 3)),
      (b'b', BmVar(2, 7)),
    ]

if __name__ == '__main__':
  unittest.main()
