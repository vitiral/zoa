
#include "./zoa.h"

// #####################################
// # zoab_tx: Data transmitting

void zoab_txData(Ring* r, Slc s, bool join) {
  U2 i = 0;
  while(true) {
    U2 len = s.len - i;
    if(len <= ZOAB_MAX_SEGLEN) { // final segment
      if(join) Ring_push(r, ZOAB_JOIN | len);
      else     Ring_push(r,             len);
      return Ring_extend(r, (Slc){s.dat + i, len});
    }
    // Join segment
    Ring_push(r, ZOAB_JOIN | ZOAB_MAX_SEGLEN);
    Ring_extend(r, (Slc){s.dat + i, ZOAB_MAX_SEGLEN});
    i += ZOAB_MAX_SEGLEN;
  }
}

void zoab_txArr(Ring* r, U1 len, U1 join) {
  ASSERT(len <= ZOAB_MAX_SEGLEN, "zoab arr must be <= MAX_SEGLEN");
  if(join) Ring_push(r, ZOAB_ARR | ZOAB_JOIN | len);
  else     Ring_push(r, ZOAB_ARR             | len);
}

void zoab_txU4(Ring* r, U4 value) { // Write up to a U4 integer (big endian)
  eprintf("Pushing: %X\n", value);
  if       (value <= 0xFF) zoab_txU1(r, value);
  else if  (value <= 0xFFFF) {
    Ring_push(r, 2);
    Ring_push(r, 0xFF & (value >> 8));
    Ring_push(r, 0xFF & value);
  } else if (value <= 0xFFFFFF) {
    Ring_push(r, 3);
    Ring_push(r, 0xFF & (value >> 16));
    Ring_push(r, 0xFF & (value >> 8));
    Ring_push(r, 0xFF & value);
  } else {
    eprintf("U4\n");
    Ring_push(r, 4);
    Ring_push(r, 0xFF & (value >> 24));
    Ring_push(r, 0xFF & (value >> 16));
    Ring_push(r, 0xFF & (value >> 8));
    Ring_push(r, 0xFF & value);
  }
}

void zoab_txStk(Ring* r, Stk* stk, U2 len) {
  len = U4_min(len, Stk_len(*stk));
  zoab_txArr(r, len, false);
  for(U2 s = stk->cap; len; s--, len--) {
    zoab_txU4(r, (U4) (stk->dat[s]));
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

U1 zoab_rxU1(Ring* r) {
  U1 len = Ring_pop(r);
  if(0 == len) return 0;
  if(1 == len) return Ring_pop(r);
  SET_ERR(Slc_ntLit("Expected U1"));
}

U4 zoab_rxU4(Ring* r) {
  U1 len = Ring_pop(r);
  eprintf("len: %u\n", len);
  ASSERT(len <= 4, "Expected U4");
  U4 v = 0;
  while(len--) {
    v = (v << 8) + Ring_pop(r);
  }
  return v;
}
