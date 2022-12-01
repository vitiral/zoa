// Zoab: serialize C types to zoa.
//
// All zoab methods work directly on a Ring data structure, which is inherently
// part of File objects and other byte IO types.
//
// There are two method types:
// 1. zoab_tx<Type>: transmits some type or sends start of data.
// 2. zoab_rx<Type>: receives some type or expects start of data.
//
// Both methods will PANIC if there is an error of any kind. It is the caller's
// job to ensure that the necessary data is available in the buffer and the
// caller is structuring it correctly. If the data cannot be trusted, it is
// recommended to create a proper panic handler which drops the relevant arena
// allocator and appropriately returns the error.
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

// #####################################
// # zoab_tx: Data transmitting

// Begin a ZOAB stream. This is used as a start signal for serial IO.
static inline void zoab_txStart(Ring* r) { Ring_extend(r, ZOA_START); }

// Send unsigned integers
static inline void zoab_txU1(Ring* r, U1 v) { Ring_push(r, 1); Ring_push(r, v); }
void zoab_txU4(Ring* r, U4 value);

// Write data of length and join bit.
void zoab_txData(Ring* r, Slc s, bool join);

// Start an array of length and join bit.
void zoab_txArr(Ring* r, U1 len, U1 join);

static inline void zoab_txNtStr(Ring* r, U1* nt, U1 join) { zoab_txData(r, Slc_frNt(nt), join); }
static inline void zoab_txArrStart(Ring* r, U1 len)  { zoab_txStart(r); zoab_txArr(r, len, false); }
static inline void zoab_txEnumStart(Ring* r, U1 var) { zoab_txArrStart(r, 2); zoab_txU1(r, var); }
static inline void zoab_txStruct(Ring* r, U1 args) { zoab_txArr(r, args + 1, false); zoab_txU1(r, args); }
static inline void zoab_txEnum(Ring* r, U1 var) { zoab_txArr(r, 2, false); zoab_txU1(r, var); }
void zoab_txStk(Ring* r, Stk* stk, U2 len);

// #####################################
// # zoab_rx: Data receiving

// Consume bytes until start is found. Return true when found.
bool zoab_rxStart(Ring* r);

U1 zoab_rxU1(Ring* r);
U4 zoab_rxU4(Ring* r);


#endif // __ZOA_H
