"""
Script for exporting zoa as other types.

Zoa is part of the civboot.org project and is released to the public domain
or licensed MIT under your discression. Modify this file in any way you wish.
Contributions are welcome.
"""
import argparse

import zoa

argP = argparse.ArgumentParser(
  description='zoa exporter. Auto-generate code types and constants from zoa.')
argP.add_argument('ty_files', help="Path/s to file or directory.")
argP.add_argument('export', help="Path to export file.")


def utf8(b):
  if isinstance(b, str): return b
  return b.decode('utf-8')

def c_struct(s: zoa.StructBase):
  out = ["typedef struct {"]
  for name, f in s._fields.items():
    out.append(f"  {utf8(f.ty.name)} {utf8(name)};")
  out.append("}  " + utf8(s.name) + ";")
  return '\n'.join(out)

def main(args):
  pass
