import io
import unittest
from zoa import *
from zoa_export import *

def assert_roundtrip(v):
  zoa = ZoaRaw.frPy(v)
  b = zoa.serialize()
  result_zoa = from_zoab(b)
  result = result_zoa.to_py()
  assert v == result

class TestUtils(unittest.TestCase):
  def testExtendWithInt(self):
    b = bytearray()
    extendWithInt(b, 0x1234567890)
    assert b == b'\x12\x34\x56\x78\x90'

    b = bytearray()
    extendWithInt(b, 0x123)
    assert b == b'\x01\x23'

  def testAttrDict(self):
    a = AttrDict({'a': 4, 'b': 7})
    assert ('a', 4) in list(a.items())
    assert a.a == 4
    assert a.b == 7
    a.a = 5
    assert a.a == 5
    a.c = 7
    assert a['c'] == 7

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
  def test_int0(self):
    res = Int(0).toZ().data
    print(res)
    assert b'' == res

  def test_int(self):
    assert b'\x42' == Int(0x42).toZ().data
    assert 0x42 == Int.frZ(ZoaRaw.new_data(b'\x42'))

    z = Int(-0x42).toZ()
    assert len(z.arr) == 1
    assert b'\x42' == z.arr[0].data
    assert -0x42 == Int.frZ(ZoaRaw.new_arr([ZoaRaw.new_data(b'\x42')]))

  def test_U1(self):
    assert b'\x42' == U1(0x42).toZ().data
    try: U1.frPy(0x100); assert(False)
    except ValueError: pass

  def test_arr_int(self):
    ai = ArrInt.frPy(range(10))
    z = ai.toZ()
    assert b''     == z.arr[0].data # special 0
    assert b'\x01' == z.arr[1].data
    assert b'\x09' == z.arr[9].data
    assert ai == ArrInt.frZ(z)
    assert repr(ai) == '[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]'

  def test_map(self):
    MapStrInt = self.env.map(Str, Int)
    m = MapStrInt.frPy({"foo": 3, "bar": 7})
    z = m.toZ()
    assert b'foo'  == z.arr[0].data
    assert b'\x03' == z.arr[1].data
    assert b'bar'  == z.arr[2].data
    assert b'\x07' == z.arr[3].data
    result = MapStrInt.frZ(z)
    assert m == result

  def test_data(self):
    b = Data(b'abc 123')
    assert b'abc 123' == b.toZ().data
    assert b == Data.frZ(ZoaRaw.new_data(b'abc 123'))
    assert repr(b) == '  61_6263_2031_3233'

  def test_struct(self):
    ty = self.env.struct(None, b'foo', odict([
        (b'a', StructField(Int)),
    ]))
    z = ZoaRaw.new_arr([
        Int(1).toZ(),  # numPositional
        Int(0x77).toZ(), # value of 'a'
    ])
    s = ty.frZ(z)
    assert s.a == 0x77
    assert z == s.toZ()

  def test_enum(self):
    ty = self.env.enum(None, b'en', [
      (b'a',     EnumVar(Int)),
      (b'b',     EnumVar(Data)),
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
    Bm = self.env.bitmap(None, b'Bm', [
        (b'a',     BmVar(0x01, 0x03)),
        (b'b',     BmVar(0x03, 0x03)),
        (b'noTop', BmVar(0x00, 0x10)),
        (b'top',   BmVar(0x10, 0x10)),
    ])
    bm = Bm();       assert 0 == bm.value
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

    bm.set_a();    assert bm.is_a();
    bm.tog_a();    assert not bm.is_a()
    bm.tog_a();    assert bm.is_a()


  def test_dyn(self):
    i = Dyn._int(4)
    assert i.ty == DynType.Int
    i = Dyn.frPy(4)
    assert i.ty == DynType.Int
    assert i.value == 4
    assert i.frZ(i.toZ()) == i
    assert repr(i) == '4'

  def test_dynArr(self):
    a = Dyn.frPyArrInt([1, 2, 3, 4])
    assert a.value == [1, 2, 3, 4]
    assert a.frZ(a.toZ()) == a
    assert repr(a) == '[1, 2, 3, 4]'

  def test_dynComplex(self):
    case = [
      b'\x20', # ArrDyn
      [[ b'\x02',   b'\x48'], # DynData    = '\x48'
       [ b'\x22', []]]        # DynArrData = []
    ]
    z = ZoaRaw.frPy(case)
    arrData = Dyn.frPyArrData([])
    expected = Dyn.frPyArrDyn([b'\x48', arrData])
    result = Dyn.frZ(z)
    assert expected.toZ() == z
    assert expected == result

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
    expected = '  68_6920_7468_6572_6520_626F_6221'
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
    assert foo._fields == odict([
      (b'a', StructField(Int)),
    ])

    p = Parser(b'struct Ab [a: Int; b: Data]')
    p.parse()
    Ab = p.env.tys[b'Ab']
    assert Ab._fields == odict([
      (b'a', StructField(Int)),
      (b'b', StructField(Data)),
    ])
    ab = Ab(a = 1, b = b'hi')
    assert ab.a == 1
    assert ab.b == b'hi'
    assert repr(ab) == "Ab(a=1, b=b'hi')"

  def test_struct_inner(self):
    p = Parser(b'struct Foo [a: Int]\nstruct Bar[a: Int; f: Foo]')
    p.parse()
    Foo = p.env.tys[b'Foo']
    Bar = p.env.tys[b'Bar']
    assert Bar._fields == odict([
      (b'a', StructField(Int)),
      (b'f', StructField(Foo)),
    ])

  def test_enum(self):
    p = Parser(b'enum E \\comment [a: Int; b: Data]')
    p.parse()
    E = p.env.tys[b'E']
    assert E._variants == [
      (b'a', EnumVar(Int)),
      (b'b', EnumVar(Data)),
    ]

  def test_bitmap(self):
    p = Parser(b'bitmap B [a 0x01 0x03; b 0x02 0x07]')
    p.parse()
    B = p.env.tys[b'B']
    assert B._variants == [
      (b'a', BmVar(1, 3)),
      (b'b', BmVar(2, 7)),
    ]

  def test_declare(self):
    p = Parser(
    b'''
    declare E;
    declare S;
    struct A [ e: E ];
    enum   B [ s: S ];

    enum   E [a: Int];
    struct S [a: Int];
    ''')
    p.parse()
    A = p.env.tys[b'A']
    B = p.env.tys[b'B']
    E = p.env.tys[b'E']
    S = p.env.tys[b'S']

    assert A._fields == {b'e': StructField(E)}
    assert S._fields == {b'a': StructField(Int)}
    assert B._variants == [(b's', EnumVar(S))]
    assert E._variants == [(b'a', EnumVar(Int))]

class TestParseValue(TestBase):
  def testInt(self):
    assert 42 == Int.parse(Parser(b'42'))
    assert 0x42 == Int.parse(Parser(b'0x42'))
    assert 0x33 == Int.parse(Parser(b'{0x33}'))

  def testData(self):
    expected = b'\x12\x34\x56\x78\x90'
    result = Data.parse(Parser(b'{1234 5678 90}'))
    assert expected == result

    expected = b'\x00\x45\x78'
    result = Data.parse(Parser(b'{00 4578}'))
    assert expected == result

  def testStrSingle(self):
    expected = "hello-bob*you-rock"
    result = Str.parse(Parser(b'  hello-bob*you-rock'))
    assert expected == result

  def testStr(self):
    expected = "hello\n bob you rock"
    result = Str.parse(Parser(b'''|\\
      hello
    \\ bob you rock\\
    |'''))
    assert expected == result

  def testArr(self):
    expected = [42, 0x37, 7777]
    result = ArrInt.parse(Parser(b'  {42, 0x37\n7777}'))
    assert expected == result

  def testMap(self):
    expected = odict([("bob", "42"), ("rachel", "his mother")])
    result = MapStrStr.parse(Parser(b'{\nbob = 42\nrachel = |his mother|\n}'))
    assert expected == result

  def testStruct(self):
    p = Parser(b'struct Foo [a: Int]\nstruct Bar[a: Int; f: Foo]')
    p.parse()
    p = Parser(b'''{
      a = 42
      f = { a = 37 }
    }''', env=p.env)
    Foo = p.env.tys[b'Foo']
    Bar = p.env.tys[b'Bar']
    expected = Bar(a=42, f=Foo(a=37))
    result = Bar.parse(p)
    assert expected == result

  def testEnum(self):
    p = Parser(b'enum E [i: Int\ns: Str]')
    p.parse()
    p = Parser(b'''i 42''', env=p.env)
    E = p.env.tys[b'E']
    expected = E(i = 42)
    result = E.parse(p)
    assert expected == result

  def testStructDefault(self):
    p = Parser(b'struct Foo [a: Int = 4]')
    p.parse()
    Foo = p.env.tys[b'Foo']
    expected = Foo(a = 4)
    result = Foo()
    assert expected == result

class TestParseConst(TestBase):
  def testInt(self):
    p = Parser(b'const a: Int = 42'); p.parse()
    assert 42 == p.env.vals[b'a']

  def testEnum(self):
    p = Parser(b'''
    enum E [i: Int  s: Str]
    const i: E = i{4}
    const s: E = s|hi there|
    '''); p.parse(); E = p.env.tys[b'E']
    assert E(i=4)          == p.env.vals[b'i']
    assert E(s="hi there") == p.env.vals[b's']

  def testStruct(self):
    p = Parser(b'''
    struct Foo [a: Int = 4]
    const f: Foo = {a = 72}
    '''); p.parse()
    Foo = p.env.tys[b'Foo']
    assert Foo(72) == p.env.vals[b'f']


STRUCT_EXPECTED = '''
typedef struct {
  Int a;
}  Foo;
'''.strip()

class TestExportC(TestBase):
  def testStruct(self):
    p = Parser(b'''struct Foo [a: Int = 4]'''); p.parse()
    Foo = p.env.tys[b'Foo']
    result = cStruct(Foo)
    assert result == STRUCT_EXPECTED

if __name__ == '__main__':
  unittest.main()
