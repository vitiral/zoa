import io
import unittest
import dataclasses

from enum import Enum
from typing import Any, Dict, List, Tuple, Iterable
from dataclasses import dataclass

ZOA_LEN_MASK = 0x3F
ZOA_JOIN = 0x80
ZOA_ARR = 0x40
ZOA_DATA = 0x00

class Eof(Exception): pass

def isbytes(v): return isinstance(v, (bytes, bytearray))

@dataclass
class ZoaRaw(object):
  data: bytearray
  arr: list["ZoaRaw"]

  @classmethod
  def from_bytes(cls, value):
    if isbytes(value): return cls.new_data(value)
    out = []
    for v in value:
      out.append(ZoaRaw.from_bytes(v))
    return cls.new_arr(out)

  def to_py(self):
    if self.data is not None: return bytes(self.data)
    if self.arr is None: raise ValueError(self)
    out = []
    for v in self.arr:
      out.append(v.to_py())
    return out

  @classmethod
  def new_arr(cls, value=None):
    return cls(data=None, arr=value if value is not None else [])

  @classmethod
  def new_data(cls, value=None):
    return cls(data=value if value is not None else bytearray(), arr=None)

  def serialize(self, bw=None):
    bw = bw if bw is not None else io.BytesIO()
    if self.data: write_data(bw, self.data)
    else:         write_arr(bw, self.arr)
    bw.seek(0)
    return bw

  def extend(self, value):
    if isbytes(value):
      if self.data is None: raise ValueError("invalid extend")
      self.data.extend(value)
    else:
      if self.arr is None: raise ValueError("invalid extend")
      self.arr.append(value)

  def get(self, value):
    if self.data is not None:
      return self.data
    return self.arr

def int_from_bytes(b: bytes):
  return int.from_bytes(b, 'big')

def write_byte(bw: io.BytesIO, v: int):
  return bw.write(v.to_bytes(1, 'big'))

def write_data(bw: io.BytesIO, data: bytes):
  if len(data) == 0:
    bw.write(b'\0') # No join bit, arr bit, or length
    return

  # write any join blocks
  i = 0
  while len(data) - i > 63:
    write_byte(bw, ZOA_JOIN | 63)
    bw.write(data[i:i+63])
    i += 63
  write_byte(bw, len(data) - i) # note: not joined
  bw.write(data[i:])

def write_arr(bw: io.BytesIO, arr: list[ZoaRaw]):
  i = 0
  while True:
    remaining = len(arr) - i
    join = ZOA_JOIN if remaining > 63 else 0
    write_byte(bw, ZOA_ARR | join | min(63, remaining))

    j = 0
    while True:
      if i == len(arr): return
      if j >= 63: break
      v = arr[i]
      if v.data  is not None: write_data(bw, v.data)
      elif v.arr is not None: write_arr(bw, v.arr)
      else: raise ValueError(v)

      j += 1
      i += 1

def readexact(br: io.BytesIO, to: bytearray, length: int):
  while length:
    got = br.read(length)
    if not got: raise Eof()
    length -= len(got)
    to.extend(got)
    if not length: break

def from_zoab(br: io.BytesIO, joinTo:ZoaRaw = None):
  out = None
  join = 0

  prev_ty = 1
  while True:
    meta = int_from_bytes(br.read(1))
    ty = ZOA_ARR & meta
    if join:
      if ty != prev_ty: raise ValueError("join different types")
    else:
      if ZOA_ARR & ty:  out = ZoaRaw.new_arr()
      else:             out = ZoaRaw.new_data()
    length = ZOA_LEN_MASK & meta

    if ty: # is arr
      for _ in range(length):
        out.arr.append(from_zoab(br))
    else:  # is data
      readexact(br, out.data, length)

    join = ZOA_JOIN & meta
    if not join:
      return out
    prev_ty = ty


def intBytesLen(v: int) -> int:
  if v <= 0xFF:       return 1
  if v <= 0xFFFF:     return 2
  if v <= 0xFFFFFF:   return 3
  if v <= 0xFFFFFFFF: return 4
  raise ValueError(f"Int too large: {v}")

class Int(int):
  name = 'Int'

  @classmethod
  def frPy(cls, *args, **kwargs): return cls(*args, **kwargs)

  @classmethod
  def frZ(cls, raw: ZoaRaw) -> int:
    if raw.arr:
      assert 1 == len(raw.arr)
      return -Int.from_bytes(raw.arr[0].data, byteorder='big')
    return Int.from_bytes(raw.data, byteorder='big')

  def toZ(self) -> ZoaRaw:
    length = intBytesLen(abs(self))
    v = abs(self).to_bytes(length, byteorder='big')
    z = ZoaRaw.new_data(v)
    if self >= 0: return z
    return ZoaRaw.new_arr([z])

class Bytes(bytes):
  name = 'Bytes'

  @classmethod
  def frPy(cls, *args, **kwargs): return cls(*args, **kwargs)
  @classmethod
  def frZ(cls, raw: ZoaRaw) -> "Bytes": return cls(raw.data)
  def toZ(self) -> ZoaRaw: return ZoaRaw.new_data(self)

@dataclass
class StructField:
  ty: Any
  zid: int = None

@dataclass(init=False)
class ArrBase(list):
  @classmethod
  def frPy(cls, l: Iterable[Any]): return cls([cls._ty.frPy(i) for i in l])
  @classmethod
  def frZ(cls, raw: ZoaRaw): return cls(cls._ty.frZ(z) for z in raw.arr)
  def toZ(self) -> ZoaRaw: return ZoaRaw.new_arr([v.toZ() for v in self])

@dataclass(init=False)
class StructBase:
  @classmethod
  def frZ(cls, z: ZoaRaw):
    args = []
    posArgs = Int.frZ(z.arr[0]) # number of positional args
    fields = iter(cls._fields)
    for pos in range(posArgs):
      _name, f = next(fields)
      assert f.zid is None
      args.append(f.ty.frZ(z.arr[1 + pos]))
    print(args)
    kwargs = {}
    byId = {f.zid: (name, f.ty) for name, f in cls._fields}
    for z in z.arr[1+posArgs:]:
      name, ty = byId[Int.frZ(zi[0])]
      kwargs[name] = ty.frZ(zi[1])
    return cls(*args, **kwargs)

  def toZ(self) -> ZoaRaw:
    # find how many positional args exist
    posArgs = 0; posArgsDone = False
    for name, f in self._fields:
      if f.zid is None: # positional arg
        if getattr(self, name) is None: posArgsDone = True
        elif posArgsDone: raise ValueError(
          f"{name} has value after previous positional arg wasn't specified")
        else: posArgs += 1

    out = [Int(posArgs).toZ()] # starts with number of positional arguments
    for name, f in self._fields:
      if f.zid is None: out.append(getattr(self, name).toZ())
      else: out.append(ZoaRaw.new_arr([f.zid, self.get(name).toZ()]))
    return ZoaRaw.new_arr(out)

@dataclass
class BmVar: # Bitmap Variant
  var: int  # the value for this variant, i.e. 0b10
  msk: int  # the mask for this variant,  i.e. 0b11

  def _setVariantClosure(varSelf):
    def closure(bitmapSelf):
      bitmapSelf.value = ((~varSelf.msk) & bitmapSelf.value) | varSelf.var
    return closure

  def _isVariantClosure(varSelf):
    def closure(bitmapSelf):
      return varSelf.msk & bitmapSelf.value == varSelf.var
    return closure

@dataclass(init=False)
class BitmapBase:
  value: int = 0

def modname(mod, name): return mod + '.' + name if mod else name

class TyEnv:
  def __init__(self):
    self.tys = {
        "Int": Int,
        "Bytes": Bytes,
    }

  def arr(self, ty: Any) -> ArrBase:
    """Create or get generic array type."""
    name = f'Array[{ty.name}]'
    existing = self.tys.get(name)
    if existing: return existing
    arrTy = type(name, (ArrBase,), {'_ty': ty, 'name': name})
    self.tys[name] = arrTy
    return arrTy

  def struct(self, mod: str, name: str, fields: List[Tuple[str, StructField]]):
    mn = modname(mod, name)
    if mn in self.tys: raise KeyError(f"Modname {mn} already exists")
    ty = dataclasses.make_dataclass(
      name,
      [(n, f.ty) for (n, f) in fields],
      bases=(StructBase,),
    )
    ty.name = mn
    ty._fields = fields
    self.tys[mn] = ty
    return ty

  def bitmap(self, mod: str, name: str, variants: List[Tuple[str, BmVar]]):
    mn = modname(mod, name)
    methods = {'name': mn}
    for n, var in variants:
      n = n[0].upper() + (n[1:] if len(n) > 1 else '') # capitalize first letter
      methods['is' + n] = var._isVariantClosure()
      methods['set' + n] = var._setVariantClosure()
    ty = type(name, (BitmapBase,), methods)
    self.tys[mn] = ty
    return ty

class TG(Enum): # Token Group
  T_NUM = 0
  T_HEX = 1
  T_ALPHA = 2
  T_SINGLE = 3
  T_SYMBOL = 4
  T_WHITE = 5

  @classmethod
  def fromChr(cls, c: int):
    if(c <= ord(' ')):                  return cls.T_WHITE;
    if(ord('0') <= c and c <= ord('9')): return cls.T_NUM;
    if(ord('a') <= c and c <= ord('f')): return cls.T_HEX;
    if(ord('A') <= c and c <= ord('F')): return cls.T_HEX;
    if(ord('g') <= c and c <= ord('z')): return cls.T_ALPHA;
    if(ord('G') <= c and c <= ord('Z')): return cls.T_ALPHA;
    raise ValueError(c)

class ParseError(RuntimeError):
  def __init__(self, line, msg): return super().__init__(f'line {line}: {msg}')

# @dataclass
# class Parser:
#   env: TyEnv = TyEnv.__init__
#   mod: str = None
#   buf: bytearray = lambda: bytearray()
#   i: int = 0
#   line: int = 1
# 
#   def token(self) -> str:
#     group, starti = None, i
#     while i < len(buf):
#       c = buf[i]; i += 1
#       if c == '\n': line += 1
#       cgroup = TG.fromChr(c)
#       if cgroup == TG.T_WHITE:
#         if group is None: continue
#         else: return buf[i-1:i]
#       if cgroup == TG.T_SINGLE:
#         return buf[i-1:i]
#       if group is None:     group = cgroup
#       elif group == cgroup: pass
#       elif (group <= T_ALPHA) and (cgroup <= T_ALPHA): pass
#       else: return buf[i-1:i]
# 
#   def peek(self) -> str:
#     starti = i
#     out = self.token()
#     i = starti
#     return out
# 
#   def parseError(self, msg): raise ParseError(self.line, msg)
#   def sugar(self, s):
#     if self.token() != s.encode('utf-8'): self.parseError(f"Expected |{s}|")
# 
#   def parseTy(self) -> Ty:
#     name = self.token()
#     # TODO: handle [ ... ] cases
#     return self.env.tys[name]
# 
#   def parseField(self) -> StructField:
#     name = self.token(); self.sugar(':')
#     # TODO: handle zid case
#     ty = self.parseTy()
#     return (name, StructField(ty=ty))
# 
#   def parseStruct(self) -> StructBase:
#     name = self.token();
#     fields = []
#     self.sugar('[')
#     while self.peek() != ']':
#       fields.append(self.parseField())
#       self.sugar(';')
#     self.sugar(']')
#     return self.env.struct(self.mod, name, fields)
# 
#   def parseFile(self):
#     while i < len(buf):
# 
