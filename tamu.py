import io
import unittest

from dataclasses import dataclass

TAMU_LEN_MASK = 0x3F
TAMU_JOIN = 0x40
TAMU_ARR = 0x80

def isbytes(v): return isinstance(v, (bytes, bytearray))

@dataclass
class San(object):
  data: bytearray
  arr: list["San"]

  @classmethod
  def from_(cls, value):
    if isbytes(value): return cls.new_data(value)
    out = []
    for v in value:
      out.append(San.from_(v))
    return cls.new_arr(out)

  @classmethod
  def new_arr(cls, value=None):
    return cls(data=None, arr=value if value is not None else [])

  @classmethod
  def new_data(cls, value=None):
    return cls(data=value if value is not None else bytearray(), arr=None)

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

  def serialize(self, bw: io.BytesIO = None):
    bw = bw if bw is not None else io.BytesIO()
    if self.data is not None:
      bw.write(self.datA)
      return to

def write_data(bw: io.BytesIO, data: bytes, join=False):
  if join: assert len(arr) <= 64
  join = TAMU_JOIN if join else 0
  if len(data) == 0:
    assert not join
    bw.write(0) # No join bit, arr bit, or length
    return

  # write any join blocks
  i = 0
  while len(data) - i > 64:
    b.write(TAMU_JOIN | 64)
    bw.write(bw, data[i:i+64])
    i += 64
  bw.write(len(data) - i) # note: not joined
  bw.write(bw, data[i:])

def write_arr(bw: io.BytesIO, arr: list[San], join=False):
  if join: assert len(arr) <= 64
  if len(arr) == 0:
    assert not join
    bw.write(TAMU_ARR)
    return

  join = TAMU_JOIN if join else 0
  bw.write(TAMU_ARR | join | min(64, len(arr)))

  # write out the first 64 values
  i = 0
  while i < 64:
    v = arr[i]
    if v.data: write_data(bw, v.data)
    else: write_arr(bw, v.arr)
    i += 1
  if not i: return

  # write out the remaining values in 64 block chunks
  while len(arr) - i > 0:
    write_arr(bw, arr[i:i+64], join=True)
    i += min(64, len(arr) - i)


def readexact(br: io.BytesIO, to: bytearray, length: int):
  while length:
    got = br.read(length)
    length -= len(got)
    to.extend(got)


def from_san(br: io.BytesIO, num:int = 1, joinTo:San = None):
  ty = br.read(1)
  if joinTo:          out = joinTo
  elif TAMU_ARR & ty: out = San.new_arr()
  else:               out = San.newData()
  length = TAMU_LEN_MASK & ty

  if not (TAMU_ARR & ty):
    if out.data is None: raise ValueError("invalid join")
    readexact(br, out.data, length)
    if TAMU_JOIN & ty:
      san(br, joinTo=out)
    return out

  if out.arr is None: raise ValueError("invalid join")
  for _ in range(length):
    out.arr.append(san(br))

  if TAMU_JOIN & ty:
    san(br, num=1, joinTo=out)

