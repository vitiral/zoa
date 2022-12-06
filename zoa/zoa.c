
#include <math.h>
#include "./zoa.h"

#define Ring_require(R, REQ)  if(Ring_remain(R) < (REQ)) return REQ
#define R0                    return 0;

// #####################################
// # zoab_tx: Data transmitting

U2 zoab_txData(Ring* r, Slc s, bool join) {
  U2 i = 0;
  while(true) {
    U2 len = s.len - i;
    if(len + 1 > Ring_remain(r)) return i;
    if(len <= ZOAB_MAX_SEGLEN) { // final segment
      if(join) Ring_push(r, ZOAB_JOIN | len);
      else     Ring_push(r,             len);
      Ring_extend(r, (Slc){s.dat + i, len});
      return 0;
    }
    // Join segment
    Ring_push(r, ZOAB_JOIN | ZOAB_MAX_SEGLEN);
    Ring_extend(r, (Slc){s.dat + i, ZOAB_MAX_SEGLEN});
    i += ZOAB_MAX_SEGLEN;
  }
}

U2 zoab_txArr(Ring* r, U1 len, U1 join) {
  if(Ring_isFull(r)) return 1;
  ASSERT(len <= ZOAB_MAX_SEGLEN, "zoab arr must be <= MAX_SEGLEN");
  if(join) Ring_push(r, ZOAB_ARR | ZOAB_JOIN | len);
  else     Ring_push(r, ZOAB_ARR             | len);
}

U2 zoab_txNtStr(Ring* r, U1* nt, U1 join) {
  return zoab_txData(r, Slc_frNt(nt), join);
}

U2 zoab_txArrStart(Ring* r, U1 len) {
  if(Ring_remain(r) < 3) return 3;
  zoab_txStart(r);
  zoab_txArr(r, len, false);
R0}

U2 zoab_txEnumStart(Ring* r, U1 var) {
  if(Ring_remain(r) < 5) return 5;
  zoab_txArrStart(r, 2);
  U1_txZoab(r, var);
R0}

U2 zoab_txStruct(Ring* r, U1 args) {
  if(Ring_remain(r) < 3) return 3;
  zoab_txArr(r, args + 1, false); U1_txZoab(r, args);
R0}

U2 zoab_txEnum(Ring* r, U1 var) {
  if(Ring_remain(r) < 3) return 3;
  zoab_txArr(r, 2, false); U1_txZoab(r, var);
R0}

U2 U1_txZoab(Ring* r, U1 v) {
  if(v == 0) {
    if(Ring_isFull(r)) return 1;
    Ring_push(r, 0);
  } else {
    Ring_require(r, 2);
    Ring_push(r, 1);
    Ring_push(r, v);
  }
R0}

U2 U4_txZoab(Ring* r, U4 value) {
  eprintf("Pushing: %X\n", value);
  if       (value <= 0xFF) return U1_txZoab(r, value);
  else if  (value <= 0xFFFF) {
    Ring_require(r, 3);
    Ring_push(r, 2);
    Ring_push(r, 0xFF & (value >> 8));
    Ring_push(r, 0xFF & value);
  } else if (value <= 0xFFFFFF) {
    Ring_require(r, 4);
    Ring_push(r, 3);
    Ring_push(r, 0xFF & (value >> 16));
    Ring_push(r, 0xFF & (value >> 8));
    Ring_push(r, 0xFF & value);
  } else {
    Ring_require(r, 5);
    Ring_push(r, 4);
    Ring_push(r, 0xFF & (value >> 24));
    Ring_push(r, 0xFF & (value >> 16));
    Ring_push(r, 0xFF & (value >> 8));
    Ring_push(r, 0xFF & value);
  }
R0}

void zoab_txStk(Ring* r, Stk* stk, U2 len) {
  len = U4_min(len, Stk_len(*stk));
  zoab_txArr(r, len, false);
  for(U2 s = stk->cap; len; s--, len--) {
    U4_txZoab(r, (U4) (stk->dat[s]));
  }
}

// #####################################
// # zoab_rx: Data receiving

bool zoab_rxStart(Ring* r) {
  bool first = false;
  while(Ring_len(r) >= 2) {
    U1 c = Ring_pop(r);
    if(first && (ZOA_START_1 == c))  return true;
    else if     (ZOA_START_0 == c)   first = true;
    else                             first = false;
  }
  return false;
}

U1 U1_rxZoab(Ring* r) {
  U1 len = Ring_pop(r);
  if(0 == len) return 0;
  if(1 == len) return Ring_pop(r);
  SET_ERR(Slc_ntLit("Expected U1"));
}

U4 U4_rxZoab(Ring* r) {
  U1 len = Ring_pop(r);
  eprintf("len: %u\n", len);
  ASSERT(len <= 4, "Expected U4");
  U4 v = 0;
  while(len--) {
    v = (v << 8) + Ring_pop(r);
  }
  return v;
}
