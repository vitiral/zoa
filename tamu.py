import io
import unittest

from dataclasses import dataclass

SAB_LEN_MASK = 0x3F
SAB_JOIN = 0x40
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
    if self.data: return self.data
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

def write_data(bw: io.BytesIO, data: bytes, join=False):
  assert join == 0 or join == SAB_JOIN
  if join: assert len(arr) <= 64
  if len(data) == 0:
    assert not join
    bw.write(b'\0') # No join bit, arr bit, or length
    return

  # write any join blocks
  i = 0
  while len(data) - i > 64:
    write_byte(bw, SAB_JOIN | 64)
    bw.write(bw, data[i:i+64])
    i += 64
  write_byte(bw, len(data) - i) # note: not joined
  bw.write(data[i:])

def write_arr(bw: io.BytesIO, arr: list[Sab], join=False):
  assert join == 0 or join == SAB_JOIN
  if join: assert len(arr) <= 64
  if len(arr) == 0:
    write_byte(bw, SAB_ARR)
    return

  write_byte(bw, SAB_ARR | join | min(64, len(arr)))

  # write out the first 64 values
  i = 0
  while i < 64 and i < len(arr):
    v = arr[i]
    if v.data  is not None:  write_data(bw, v.data)
    elif v.arr is not None: write_arr(bw, v.arr)
    else: raise ValueError(v)
    i += 1
  if i == len(arr): return

  # write out the remaining values in 64 block chunks
  while len(arr) - i > 0:
    write_arr(bw, arr[i:i+64], join=True)
    i += min(64, len(arr) - i)

def readexact(br: io.BytesIO, to: bytearray, length: int):
  while length:
    got = br.read(length)
    length -= len(got)
    to.extend(got)

def from_sab(br: io.BytesIO, num:int = 1, joinTo:Sab = None):
  if isinstance(br, bytes): br = io.BytesIo(br)

  ty = int_from_bytes(br.read(1))
  if joinTo:          out = joinTo
  elif SAB_ARR & ty:  out = Sab.new_arr()
  else:               out = Sab.new_data()
  length = SAB_LEN_MASK & ty

  if not (SAB_ARR & ty): # if not arr
    if out.data is None: raise ValueError("invalid join")
    readexact(br, out.data, length)
    if SAB_JOIN & ty:
      from_sab(br, joinTo=out)
    return out

  # arr
  if out.arr is None: raise ValueError("invalid join")
  for _ in range(length):
    out.arr.append(from_sab(br))

  if SAB_JOIN & ty:
    from_sab(br, num=1, joinTo=out)
  return out
