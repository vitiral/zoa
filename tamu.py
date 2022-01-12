import io
import unittest

from dataclasses import dataclass

SAB_LEN_MASK = 0x3F
SAB_JOIN = 0x40
SAB_DATA = 0x00
SAB_ARR = 0x80

def isbytes(v): return isinstance(v, (bytes, bytearray))

@dataclass
class Sab(object):
  data: bytearray
  arr: list["Sab"]

  @classmethod
  def from_(cls, value):
    if isbytes(value): return cls.new_data(value)
    out = []
    for v in value:
      out.append(Sab.from_(v))
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
    write_byte(bw, SAB_JOIN | 63)
    bw.write(data[i:i+63])
    i += 63
  write_byte(bw, len(data) - i) # note: not joined
  bw.write(data[i:])

def write_arr(bw: io.BytesIO, arr: list[Sab]):
  i = 0
  while True:
    join = SAB_JOIN if len(arr) - i > 63 else 0
    write_byte(bw, SAB_ARR | join | min(63, len(arr)))

    j = 0
    while True:
      if i == len(arr): return
      if j >= 63: break

      print(f"i={i}  j={j}")
      v = arr[i]

      if v.data  is not None: write_data(bw, v.data)
      elif v.arr is not None: write_arr(bw, v.arr)
      else: raise ValueError(v)

      j += 1
      i += 1

def readexact(br: io.BytesIO, to: bytearray, length: int):
  while length:
    got = br.read(length)
    length -= len(got)
    to.extend(got)

def from_sab(br: io.BytesIO, joinTo:Sab = None):
  out = None
  join = 0

  prev_ty = 1
  while True:
    meta = int_from_bytes(br.read(1))
    ty = SAB_ARR & ty
    if join and ty != prev_ty:
      raise ValueError("join different types")
    else:
      if SAB_ARR & ty:  out = Sab.new_arr()
      else:             out = Sab.new_data()
    lenth = SAB_LEN_MASK & meta

    if ty: # is arr
      for _ in range(length):
        out.append(from_sab(br))
    else:  # is data
      readexact(br, out.data, length)

    join = SAB_JOIN & ty
    if not join:
      return out
