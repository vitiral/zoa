// Zoab: serialize C types to zoa.
//
// All zoab methods work directly on a Ring data structure, which is inherently
// part of File objects and other byte IO types.
//
// There are two method types:
// 1. zoab_tx<Type>: transmits some type or sends start of data.
// 2. zoab_rx<Type>: receives some type or expects start of data.
//
// The "core" types behave by returning 0 on success, and on failure they return
// the number of bytes the Ring buffer needs to be. They take in the Ring buffer
// directly to keep their implementation as simple and testable as possible.
//
// For generated code, the behavior depends:
// * For structs of all-basic types (no embedded structs, lists, etc) it returns
//   0 on success, else the current field index (base-1) that hasn't been sent.
// * For more complicated types, it requires a Writer type. The write method
//   gets called when the ring is too full.

#ifndef __ZOA_H
#define __ZOA_H

#include "civ/civ.h"

#define ZOA_START_0 0x80
#define ZOA_START_1 0x03

#define ZOA_START  Slc_ntLit("\x80\x03")

#define ZOAB_MAX_SEGLEN      0x63
#define ZOAB_TY              0xC0
#define ZOAB_JOIN            0x80
#define ZOAB_ARR             0x40
#define ZOAB_PTR             0xC0

U2 U1_txZoab(Ring* r, U1 v);
U2 U4_txZoab(Ring* r, U4 value);

U1 U1_rxZoab(Ring* r);
U4 U4_rxZoab(Ring* r);

// #####################################
// # zoab_tx: Data transmitting

// Begin a ZOAB stream. This is used as a start signal for serial IO.
static inline U2 zoab_txStart(Ring* r) {
  if(Ring_remain(r) < 2) return 2;
  Ring_extend(r, ZOA_START);
}

// Write data of length and join bit.
//
// Return the amount of data written. This should be added to s.dat and
// subtracted from s.len after the ring has been drained.
U2 zoab_txData(Ring* r, Slc s, bool join);

// Start an array of length and join bit.
U2 zoab_txArr(Ring* r, U1 len, U1 join);

U2 zoab_txNtStr(Ring* r, U1* nt, U1 join);

U2 zoab_txArrStart(Ring* r, U1 len);

U2 zoab_txEnumStart(Ring* r, U1 var);

U2 zoab_txStruct(Ring* r, U1 args);

U2 zoab_txEnum(Ring* r, U1 var);

void zoab_txStk(Ring* r, Stk* stk, U2 len);

// #####################################
// # zoab_rx: Data receiving

// Consume bytes until start is found. Return true when found.
bool zoab_rxStart(Ring* r);

#endif // __ZOA_H
